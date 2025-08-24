# Catch AttributeError on DaViT

```bash
AttributeError: 'DaViT' object has no attribute '_initialize_weights'
```

This error occurs when transformers is 4.52.1 or larger as stated in [this discussion](https://huggingface.co/microsoft/Florence-2-large/discussions/104)

One way to test for this is

```bash
SKIP_MODEL_TESTS=false pytest tests/image_processor/test_florence_processor.py -s -v -k 'test_real_florence_processor'
```

