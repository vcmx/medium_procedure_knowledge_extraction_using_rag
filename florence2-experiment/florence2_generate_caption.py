import os
import sys
from unittest.mock import patch

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

# Workaround for flash_attn import issue on Mac MPS
try:
    from transformers.dynamic_module_utils import get_imports

    def fixed_get_imports(filename: str | os.PathLike) -> list[str]:
        if not str(filename).endswith("/modeling_florence2.py"):
            return get_imports(filename)
        imports = get_imports(filename)
        if "flash_attn" in imports:
            imports.remove("flash_attn")
        return imports
except ImportError:
    fixed_get_imports = None


def load_image_from_path(path):
    try:
        image = Image.open(path).convert("RGB")
        return image
    except Exception as e:
        print(f"Error loading image from path: {e}")
        return None


def run_florence2_task(image, task_prompt, model, processor, device, torch_dtype):
    if image is None:
        return "Error: Image not loaded."
    prompt = task_prompt
    inputs = processor(text=prompt, images=image, return_tensors="pt").to(
        device, dtype=torch_dtype if device.type != "cpu" else torch.float32
    )
    try:
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            early_stopping=False,
            do_sample=False,
            num_beams=3,
        )
        generated_text = processor.batch_decode(
            generated_ids, skip_special_tokens=False
        )[0]
        image_size = image.size
        parsed_answer = processor.post_process_generation(
            generated_text, task=task_prompt, image_size=image_size
        )
    except Exception as e:
        print(f"Error during model generation or post-processing: {e}")
        try:
            generated_text_fallback = processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]
            return (
                f"Raw model output (post-processing error): {generated_text_fallback}"
            )
        except:
            return (
                "Error in both model generation/post-processing and fallback decoding."
            )
    return parsed_answer


def main():
    # if len(sys.argv) < 2:
    #     print("Usage: python florence2_generate_caption.py /path/to/image.jpeg")
    #     sys.exit(1)
    # image_path = sys.argv[1]
    image_path = "input-pdfs/sample-images/sample.jpeg"  # Hardcoded image path
    # model_id = "microsoft/Florence-2-large-ft"  # finetuned model
    model_id = "microsoft/Florence-2-large"  # base model
    # Device selection: prefer MPS, then CUDA, then CPU
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        torch_dtype = torch.float32  # MPS only supports float32
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        torch_dtype = torch.float16
    else:
        device = torch.device("cpu")
        torch_dtype = torch.float32
    print(f"Using device: {device}")

    def load_model_and_processor():
        # Only use the 'dtype' argument for CUDA devices. Florence-2's custom model code does not accept 'dtype' for MPS/CPU,
        # and passing it will cause an error. For MPS/CPU, omit 'dtype' to ensure compatibility and faster loading.
        if device.type == "cuda":
            model = AutoModelForCausalLM.from_pretrained(
                model_id, trust_remote_code=True, revision="main", dtype=torch_dtype
            ).to(device)
        else:
            model = AutoModelForCausalLM.from_pretrained(
                model_id, trust_remote_code=True, revision="main"
            ).to(device)
        processor = AutoProcessor.from_pretrained(
            model_id, trust_remote_code=True, revision="main"
        )
        return model, processor

    if fixed_get_imports is not None:
        with patch("transformers.dynamic_module_utils.get_imports", fixed_get_imports):
            model, processor = load_model_and_processor()
    else:
        model, processor = load_model_and_processor()

    print(f"Model loaded on device: {device}")
    image = load_image_from_path(image_path)
    if image is None:
        print(f"Could not load the image at {image_path}")
        sys.exit(1)
    task_prompt_caption = "<MORE_DETAILED_CAPTION>"
    print("--- Running: Detailed Caption ---")
    caption_results = run_florence2_task(
        image, task_prompt_caption, model, processor, device, torch_dtype
    )
    print("\nResult:")
    print(caption_results)


if __name__ == "__main__":
    main()
