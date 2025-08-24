# Data Preparation Pipeline

This document provides instructions on how to run the data preparation pipeline, which processes PDF documents, captions images, generates embeddings, and stores the results in a vector database.

## 1. Prerequisites

### Activate Virtual Environment

Before running the pipeline, ensure you have activated the project's virtual environment.

```bash
source .venv/bin/activate
```

### Environment Variables

For certain functionalities, you will need to set up a `.env` file in the root of the project.

- To use the **Hugging Face Inference API**, create a `.env` file and add your API key:

  ```
  HUGGINGFACE_API_KEY="your_hugging_face_api_key_here"
  ```

- To use the **OpenRouter API** for image processing, add your key:

  ```
  OPENROUTER_API_KEY="your_openrouter_api_key_here"
  ```

The pipeline will automatically load these keys.

## 2. Running the Pipeline

The main script for running the data preparation pipeline is `run_pipeline.py`. You can select different implementations for image captioning and text embedding using command-line arguments.

### Example 1: Using Local Processors

This command runs the pipeline using the default local models for both image captioning (Florence-2) and embedding (CLIP). This is resource-intensive and may be slow.

```bash
python run_pipeline.py --pdf_path input-pdfs/your-document.pdf --output_dir output
```

### Example 2: Using Hugging Face API for Faster Processing

This command offloads the compute-intensive tasks to the Hugging Face Inference API. This is much faster and recommended if you have an API key.

```bash
python run_pipeline.py \
    --pdf_path input-pdfs/your-document.pdf \
    --output_dir output \
    --image_processor_impl huggingface \
    --embedder_impl huggingface
```

### Example 3: Wiping the Database Before Running

If you want to start with a clean vector database, use the `--wipe_db` flag. This will delete the directory specified in `--storage_kwargs` (by default, `./chroma_db`) before processing.

```bash
python run_pipeline.py \
    --pdf_path input-pdfs/your-document.pdf \
    --output_dir output \
    --wipe_db
```

### Example 4: Mixing Local and Remote Processors

You can mix and match implementations. For example, you can use the fast Hugging Face API for image captioning but use a specific local model (`siglip`) for embeddings.

```bash
python run_pipeline.py \
    --pdf_path input-pdfs/your-document.pdf \
    --output_dir output \
    --image_processor_impl huggingface \
    --embedder_impl siglip
```

### Example 5: Specifying Different Models and Storage Path

This example shows how to specify a different embedding model on the Hugging Face Hub and also directs the ChromaDB storage to a custom directory.

```bash
python run_pipeline.py \
    --pdf_path input-pdfs/your-document.pdf \
    --output_dir output \
    --embedder_impl huggingface \
    --embedder_kwargs '{"model_name": "BAAI/bge-small-en-v1.5"}' \
    --storage_kwargs '{"persist_dir": "./custom_db"}'
```

### Example 6: Using a Pre-processed Directory

If you have already run the PDF extraction step (e.g., using Marker) and have a directory with markdown files and images, you can run the pipeline on that directory directly.

```bash
python run_pipeline.py --pre_processed_dir path/to/your/pre-processed-folder --output_dir output
```

### Example 7: Wipe and use huggingface implementations

```bash
python run_pipeline.py \
    --pdf_path input-pdfs/your-document.pdf \
    --output_dir output \
    --image_processor_impl huggingface \
    --embedder_impl huggingface \
    --wipe_db
```

## 3. Command-Line Arguments

- `--pdf_path`: Path to the input PDF file. One of this or `--pre_processed_dir` is required.
- `--pre_processed_dir`: Path to a directory with existing markdown and image files. One of this or `--pdf_path` is required.
- `--output_dir`: **Required**. Directory to save intermediate files and logs.
- `--wipe_db`: If included, this flag will delete the existing vector database before running the pipeline. The database location is determined by `storage_kwargs`. **Default: Not set.**
- `--image_processor_impl`: Choose the image processor.
  - Options: `local`, `huggingface`, `openrouter`.
  - **Default: `local`**, which runs the computationally intensive Florence-2 model on your local machine.
- `--embedder_impl`: Choose the embedder.
  - Options: `clip`, `siglip`, `huggingface`.
  - **Default: `clip`**, which runs the computationally intensive CLIP model on your local machine.
- `--image_processor_kwargs`: JSON string with arguments for the image processor. For example, to use a different local model: `'{"model_name": "Qwen/Qwen-VL-Chat"}'`.
- `--embedder_kwargs`: JSON string with arguments for the embedder. For example, to use a specific model on Hugging Face: `'{"model_name": "sentence-transformers/all-MiniLM-L6-v2"}'`.
- `--storage_backend`: The vector database to use. **Default: `chroma`**.
- `--storage_kwargs`: JSON string with arguments for the storage manager. **Default: `'{"persist_dir": "./chroma_db"}'`**. This path is used by the `--wipe_db` command.

## 4. Relevant Files

This section provides an overview of the key files involved in the data preparation pipeline.

- **`run_pipeline.py`**: The main entry point script for executing the pipeline. It parses command-line arguments and orchestrates the different modules.
- **`src/modules/pipeline/multimodal_rag_pipeline.py`**: Contains the core logic for the pipeline, coordinating the extraction, processing, and storage steps.
- **`src/modules/image_processor/factory.py`**: A factory for creating different image processor instances (e.g., local, Hugging Face, OpenRouter). This allows for easily switching between implementations.
- **`src/modules/embeddings/factory.py`**: A factory for creating different embedding model instances (e.g., local CLIP, Hugging Face).
- **`src/modules/image_processor/florence_huggingface_processor.py`**: The implementation for generating image captions using the Hugging Face Inference API.
- **`src/modules/embeddings/huggingface_hub.py`**: The implementation for generating text and image embeddings using the Hugging Face Inference API.
- **`src/modules/image_processor/base.py`**: An abstract base class that defines the common interface for all image processors, ensuring consistency.
- **`.env`**: A file to store sensitive API keys (`HUGGINGFACE_API_KEY`, `OPENROUTER_API_KEY`). This file should not be committed to version control.
