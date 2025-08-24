This repo contains the key codes that were deployed in our prototype general-purpose LLM system for extracting procedure knowledge from technical documents, such as engineering maintenance manuals, without needing dataset annotation or model fine-tuning.

## Project Overview 
The complete project prototype uses Streamlit as a frontend interface and CHromaDB as a Vector Store. The project structure is as illustrated below:
```
.
├── setup.py              # Package setup file
├── pyproject.toml        # Packaging config
├── chroma_db             # Embedding management
├── src/                  # Source code
│   ├── __init__.py
│   └── modules/          # Contains all processing modules
│       └── agent/        # Codes for Agentic architecture
│       └── embedding/    # Embedding processing
│       └── evaluation/      # Qualitatively evaluate output with GEval and RAGAS
│       └── image_processor/ # PDF image caption generation
│       └── pdf_processor/   # PDF processing using Marker
│       └── pipeline/        # Pipeline modules
│       └── query_analyzer/  # Screen and refine initial user query
│       └── semantic_chunker/# Two-Step Hierarchical Chunking to achieve high relevance
│       └── storage_manager/
│       └── tools/
│       └── utils/
│       └── pdf_processor/
├── input-pdfs/     # Input PDF files
└── output/         # Output of processed Markdowns & images captions extracted from input PDF files
```

Dependencies:
- marker-pdf: PDF processing
- transformers: For Florence-2 model
- torch: Deep learning framework
- Pillow: Image processing
- chromadb: Vector storage

## Selected Key Modules (as described in the accompanying Medium article)
These are modules referenced in our Medium article for sharing with like-minded researchers and collaborators who may be pursuing similar research questions (ordered in the sequence of appearance in the article):

**Multimodal RAG Pipeline**
* **multimodal_rag_pipeline.py**: Part of the two-step hierarchical chunking approach where the input PDF is first divided into smaller sections using Marker, based on the headers identified. Code contain the core logic for the pipeline, coordinating the extraction, processing, and storage steps.
* **processor.py**: Text content is further broken down into smaller semantically coherent chunks.
* **florence_local_processor.py**: Transforms vital visual information from the extracted images into text format that can be processed alongside the text content. The implementation is for generating text and image embeddings using the Hugging Face Inference API.
* **factory.py**: Vector Embedding Generation with CLIP and Qwen3. This was set up to evaluate if model selection is a critical consideration that will determine the performance of the procedure knowledge extraction tool. This creates different image processor instances (e.g., local, Hugging Face, OpenRouter) and allows for easily switching between implementations.

**Improving Inference**
* **rag_with_chroma.py**: Implements Maximal Marginal Relevance (MMR) to have greater diversity in the retrieved document. It also incorporates BM25 with Reciprocal Rank Fusion to combine traditional keyword-based search with semantic similarity scoring.

**Multi-Agent Architecturen**
* **simple_supervisor_agent.py**: Implements the Multi-Agent architecture using LangGraph-based agentic flow to assign specific roles to individual agents, allowing each agent to focus on specific tasks.

**Evaluation**
* **evaluator.py**: Two approaches, namely RAGAS and GEval, to evaluate the effectiveness of our enhanced LLM-RAG engine for procedure knowledge extraction.


## Setting Up
*   We recommend deploying the codes using Python 3.12, and to set up a virtual environment before installing the necessary packages
*   Use the appropriate `requirements.txt`. `requirements.txt` is for main branch to run the first 3 modes: simple rag, eval mode, multi agent mode. `requirements-prep.txt` for pipeline processing in main branch. `requirements-query-analysis.txt` for the advanced agent mode.
