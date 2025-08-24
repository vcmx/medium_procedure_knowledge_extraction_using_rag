# ADR 005: Multimodal RAG Pipeline Architecture

## Status

Accepted

## Context

The system needs to process PDF documents containing both text and images, and make them searchable through a vector database. This requires a pipeline that can:

1. Extract and process both text and images from PDFs
2. Generate meaningful chunks that preserve context
3. Create embeddings that capture both textual and visual information
4. Store the processed content in a vector database for efficient retrieval

## Decision

We will implement a multimodal RAG pipeline that processes PDFs through the following stages:

### 1. PDF Processing Stage

- Uses `PDFProcessor` to extract sections and images from PDFs
- Maintains document structure by preserving section hierarchy
- Extracts images and stores them in an output directory

Example Log Output:
```
2025-05-25 16:03:00,861 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Extracted 203 sections
2025-05-25 16:03:00,861 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Section: **ENGINE SECTION 2** (Level 1, Page 1)
2025-05-25 16:03:00,861 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Number of images in section: 0
2025-05-25 16:03:00,861 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Content preview:
This service manual has been prepared to provide SUBARU service personnel with the necessary information and data for the correct maintenance and repair of SUBARU vehicles.

This manual includes the ...
```

### 2. Content Processing Stage

- **Text Processing**:
  - Uses `TextProcessor` to chunk text content
  - Preserves metadata like section title, level, and page number
  - Creates semantically meaningful chunks

Example Log Output (Text Chunking):
```
2025-05-25 16:03:00,861 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Processing text into chunks
... (Log lines for actual chunk content and metadata would appear here)
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Created 1 text chunks
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Chunk 1 preview: This service manual has been prepared to provide SUBARU service personnel with the necessary information and data for the correct maintenance and repair of SUBARU vehicles.

This manual includes the ...
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Chunk metadata: {'title': '**ENGINE SECTION 2**', 'level': 1, 'page_number': 1}
```

- **Image Processing**:
  - Uses `FlorenceLocalImageProcessor` for image captioning
  - Generates descriptive captions for each image
  - Maintains association between images and their sections

Example Log Output (Image Captioning - conceptual, as no images in provided logs for this section):
```
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Processing image: output_dir/some_image.jpg
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Generated caption: A detailed diagram of the engine components.
```

### 3. Embedding Generation Stage

- Uses `EmbedderFactory` to create embeddings
- Supports multiple embedding models (CLIP, SigLIP)
- Generates embeddings for combined text and image captions

Example Log Output:
```
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Combined text preview: This service manual has been prepared to provide SUBARU service personnel with the necessary information and data for the correct maintenance and repair of SUBARU vehicles.

This manual includes the ...
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Generating embeddings
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Embedding shape: (512,)
```

### 4. Storage Stage

- Uses `StorageManagerFactory` for vector database operations
- Supports multiple storage backends (Chroma, Falkor)
- Stores chunks with rich metadata including:
  - Section information
  - Image paths and captions
  - Document structure
  - Page numbers

Example Log Output:
```
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Metadata: ChunkMetadata(title='**ENGINE SECTION 2**', level=1, page_number=1, section_path=['**ENGINE SECTION 2**'], images=[], additional_metadata={'image_paths': [], 'section_level': 0})
2025-05-25 16:03:00,862 - src.modules.pipeline.multimodal_rag_pipeline - INFO - Storing in vector database
```

## Consequences

### Positive

- **Rich Context Preservation**: By combining text chunks with image captions, the system maintains the relationship between text and images
- **Flexible Architecture**: The factory pattern allows easy swapping of components (embedding models, storage backends)
- **Structured Storage**: Metadata preservation enables sophisticated retrieval strategies
- **Scalable Processing**: Each stage is modular and can be optimized independently

### Negative

- **Complexity**: The pipeline requires multiple processing stages and careful coordination
- **Resource Intensive**: Image processing and embedding generation can be computationally expensive
- **Storage Overhead**: Storing both text and image information increases storage requirements

### Neutral

- The system requires careful tuning of chunk sizes and embedding models
- Performance depends on the quality of image captioning
- Retrieval quality depends on the effectiveness of the embedding models

## Implementation Notes

- The pipeline is implemented in `multimodal_rag_pipeline.py`
- Each stage is modular and can be configured through parameters
- The system supports both local and remote processing options
- Error handling and validation should be added at each stage
- Important! - the images should be serialized into their Path and caption and then stored into the vector db. We will NOT store the base64 encoded versions of the image.