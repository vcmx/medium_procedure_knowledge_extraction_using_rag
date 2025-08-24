# Decision: Use 'dtype' Only for CUDA in florence2_generate_caption.py

## Background

The Florence-2 model (from Microsoft, via HuggingFace) is designed to run on various devices: CUDA (NVIDIA GPU), MPS (Apple Silicon), and CPU. The model loading API (`from_pretrained`) in HuggingFace Transformers allows specifying a `dtype` argument to control tensor precision (e.g., float16 for CUDA, float32 for CPU/MPS).

## Problem

Florence-2's custom model code does **not** accept the `dtype` argument when running on MPS or CPU. Passing `dtype` in these cases causes an error:

```
Florence2ForConditionalGeneration.__init__() got an unexpected keyword argument 'dtype'
```

## Solution

In `florence2_generate_caption.py`, we:

- Only pass the `dtype` argument to `from_pretrained` if the device is CUDA.
- For MPS or CPU, we omit `dtype` entirely.
- This avoids unnecessary errors and speeds up model loading.

## Code Snippet

```python
if device.type == "cuda":
    model = AutoModelForCausalLM.from_pretrained(
        model_id, trust_remote_code=True, revision="main", dtype=torch_dtype
    ).to(device)
else:
    model = AutoModelForCausalLM.from_pretrained(
        model_id, trust_remote_code=True, revision="main"
    ).to(device)
```

## Rationale

- This approach is robust to Florence-2's custom code and ensures compatibility across all platforms.
- It also avoids the need for fallback logic and makes the script faster and cleaner.

---

**Last updated:** 2024-07-06
