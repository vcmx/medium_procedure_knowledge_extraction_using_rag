This repo contains the key codes that where deployed in our prototype general-purpose LLM system for extracting procedure knowledge from technical documents, such as engineering maintenance manuals, without needing dataset annotation or model fine-tuning.

## Project Overview 
The complete project prototype uses Streamlit as frontend interface and CHromaDB as Vector Store. The project structure is as illustrated below:
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

## Key Modules
These are modules mentioned in our Medium article {} and shared here with like-minded researchers and collaborators pursuing similar research questions. The branches include:

- Simple VLM-RAG mode to understand flattened PDF technical manuals
- Preparation of the vector store (this uses the `run_pipeline.py`)
- Eval mode
- simple multi agent mode with MCP for inventory check agent, web search, and a RAG agent
- advanced agent mode with more robust query analysis [feature/advanced-rag-functions](https://github.com/simkimsia/genai-202504-team-1/tree/feature/advanced-rag-functions)
- Query-Answering (this uses the streamlit and output folder and `rag_storage` folder)

**Multimodal RAG Pipeline:**
- **multimodal_rag_pipeline.py**: Two-Step Hierarchical Chunking where the input PDF is first divided into smaller sections using Marker, based on the headers identified.
- **processor.py**: Text content is further broken down into smaller semantically coherent chunks
- **florence_local_processor.py**: transform vital visual information from the extracted images into text format that can be processed alongside the text content

**Improved Inference**
- **factory.py**: Vector Embedding Generation with CLIP and Qwen3. This allowed us to evaluate if whether model selection is a critical consideration that will determine the performance of the procedure knowledge extraction tool
- **rag_with_chroma.py**: Maximal Marginal Relevance (MMR) to introduce diversity in the retrieved document. It also incorporated BM25 with Reciprocal Rank Fusion to combine traditional keyword-based search with semantic similarity scoring.

**Agentic Design**
- **simple_supervisor_agent.py**: Multi-Agent architecture implemented using LangGraph-based agentic flow to assign specific roles to individual agents, allowing each agent to focus on specific tasks.

**Evaluation**
- **evaluator.py**: Two approaches, namely RAGAS and GEval, to evaluate the effectiveness of our enhanced LLM-RAG engine for procedure knowledge extraction.

run_pipeline.py: The main entry point script for executing the pipeline. It parses command-line arguments and orchestrates the different modules.
src/modules/pipeline/multimodal_rag_pipeline.py: Contains the core logic for the pipeline, coordinating the extraction, processing, and storage steps.
src/modules/image_processor/factory.py: A factory for creating different image processor instances (e.g., local, Hugging Face, OpenRouter). This allows for easily switching between implementations.
src/modules/embeddings/factory.py: A factory for creating different embedding model instances (e.g., local CLIP, Hugging Face).
src/modules/image_processor/florence_huggingface_processor.py: The implementation for generating image captions using the Hugging Face Inference API.
src/modules/embeddings/huggingface_hub.py: The implementation for generating text and image embeddings using the Hugging Face Inference API.
src/modules/image_processor/base.py: An abstract base class that defines the common interface for all image processors, ensuring consistency.
.env: A file to store sensitive API keys (HUGGINGFACE_API_KEY, OPENROUTER_API_KEY). This file should not be committed to version control.

Key Process Phases:

1. Preparation of the vector store (this uses the `run_pipeline.py`)
2. Query-Answering (this uses the streamlit and output folder and `rag_storage` folder)


## Tips and Recommendations
1. We recommend deploying the codes using Python 3.12, and to set up a virtual environment before installing the necessary packages

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```
2. Use `main` branch
3. Use the appropriate `requirements.txt`
   1. `requirements.txt` is for main branch to run the first 3 modes: simple rag, eval mode, multi agent mode
   2. `requirements-prep.txt` for pipeline processing in main branch
   3. `requirements-query-analysis.txt` for advanced agent mode in `feature/advanced-rag-functions` branch
