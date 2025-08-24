# Decision: Patch flash_attn Import for Florence-2 on Mac MPS

## Background

When running the Florence-2 model (from Microsoft, via HuggingFace) on Mac (MPS backend), the model's custom code attempts to import `flash_attn`, a dependency that is not available or supported on Mac/MPS. This causes import errors and prevents the model from loading.

This issue is discussed in detail in the HuggingFace community: [Florence-2-large-ft Discussion #4](https://huggingface.co/microsoft/Florence-2-large-ft/discussions/4).

## Problem

Florence-2's dynamic import logic tries to import `flash_attn` even when it is not needed (i.e., on non-CUDA devices). This results in an error on Mac/MPS:

```
ModuleNotFoundError: No module named 'flash_attn'
```

## Solution

A workaround is to patch the `get_imports` function in HuggingFace's `dynamic_module_utils` so that it skips importing `flash_attn` when loading `modeling_florence2.py`. This allows the model to load and run on Mac/MPS and CPU, where `flash_attn` is not required.

## Code Snippet

```python
from unittest.mock import patch
import os
from transformers.dynamic_module_utils import get_imports

def fixed_get_imports(filename: str | os.PathLike) -> list[str]:
    if os.path.basename(filename) != "modeling_florence2.py":
        return get_imports(filename)
    imports = get_imports(filename)
    if "flash_attn" in imports:
        imports.remove("flash_attn")
    return imports

with patch("transformers.dynamic_module_utils.get_imports", fixed_get_imports):
    # Model loading code here
```

## Rationale

- This patch is necessary for running Florence-2 on Mac/MPS and CPU, where `flash_attn` is not available.
- It is a community-accepted workaround and is referenced in the official HuggingFace discussion.
- The patch is robust across platforms if you use `os.path.basename` for filename matching.

---

**Reference:** [Florence-2-large-ft Discussion #4](https://huggingface.co/microsoft/Florence-2-large-ft/discussions/4)

**Last updated:** 2024-07-06
