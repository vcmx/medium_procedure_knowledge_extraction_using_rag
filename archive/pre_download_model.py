"""
This script pre-downloads and caches models from the Hugging Face Hub.
Running this once will ensure that the main application can load the models
from the local cache without needing to download them on the fly, which can
prevent network errors and rate-limiting issues.

This is particularly useful when using frameworks like Streamlit that might
trigger model re-downloads on script reloads.
"""

from transformers import (  # Add any other required model or processor classes here
    AutoModel,
    AutoProcessor,
    AutoTokenizer,
)

# --- Models to Pre-download ---
# For most models, you can just add the model identifier to the SIMPLE_MODELS list.
# These will be downloaded using AutoModel and AutoProcessor.
SIMPLE_MODELS = [
    "openai/clip-vit-base-patch32",
]

# For models that require special configurations (e.g., trust_remote_code=True,
# or specific model classes), add them to the ADVANCED_MODELS list.
# Each entry is a dictionary specifying the configuration.
#
# Required keys:
#   - "id": The model identifier from Hugging Face.
#
# Optional keys:
#   - "model_class": The specific model class to use (e.g., AutoModelForCausalLM).
#                    Defaults to AutoModel.
#   - "processor_class": The specific processor class to use. Set to `None` if the
#                        model has no processor. Defaults to AutoProcessor.
#
# Any other key-value pairs in the dictionary will be passed as keyword arguments
# to the `from_pretrained` method of the model and processor classes.
# For example, to pass `trust_remote_code=True`, simply add
# `"trust_remote_code": True` to the dictionary.
ADVANCED_MODELS = [
    {
        "id": "Qwen/Qwen3-Embedding-4B",
        "processor_class": AutoTokenizer,
        "trust_remote_code": True,
    },
    # {
    #     "id": "microsoft/Florence-2-large",
    #     "model_class": AutoModelForCausalLM,
    #     "trust_remote_code": True,
    # },
]


def download_model(model_config: dict):
    """
    Downloads a model and its processor from the Hugging Face Hub based on the
    provided configuration.
    """
    # Make a copy to avoid modifying the original dict
    config = model_config.copy()

    model_id = config.pop("id")
    ModelClass = config.pop("model_class", AutoModel)
    ProcessorClass = config.pop("processor_class", AutoProcessor)

    # The rest of the keys in config are kwargs for from_pretrained
    kwargs = config

    print(f"-> Downloading: {model_id}")

    try:
        if ModelClass:
            ModelClass.from_pretrained(model_id, **kwargs)

        if ProcessorClass:
            ProcessorClass.from_pretrained(model_id, **kwargs)

        print(f"   [SUCCESS] Cached {model_id}")
    except Exception as e:
        print(f"   [ERROR] Failed to download {model_id}: {e}")


def main():
    """Main function to download all specified models."""
    print("--- Starting Model Pre-download ---")

    # Combine simple and advanced models into a single list of configurations
    all_models_to_download = [
        {"id": model_id} for model_id in SIMPLE_MODELS
    ] + ADVANCED_MODELS

    for model_config in all_models_to_download:
        download_model(model_config)

    print("\n--- Pre-download Complete ---")
    print(
        "You can now run the main application. Models will be loaded from the local cache."
    )


if __name__ == "__main__":
    main()
