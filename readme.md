## Preamble
This repo was created to build a general-purpose LLM system that accurately extracts procedure knowledge from technical documents, such as engineering maintenance manuals, without dataset annotation or model fine-tuning?

## Project Overview 
1. The complete project prototype uses Streamlit as frontend interface and CHromaDB as Vector Store. The project structure is as illustrated below:
```
.
├── setup.py              # Package setup file
├── pyproject.toml        # Packaging config
├── src/                  # Source code
│   ├── __init__.py
│   └── modules/
│       └── pdf_processor/
│           ├── __init__.py
│           ├── processor.py
│           └── example.py
├── tests/               # Test files
│   ├── conftest.py
│   └── test_pdf_processor.py
├── input-pdfs/          # Input PDF files
└── output/         # Output directory holding processed Markdowns and images extracted from input PDF files
```

2. Organisation:
- `src/modules/`: Contains all processing modules
  - `pdf_processor/`: PDF processing using Marker
- `tests/`: Test files
- `input-pdfs/`: Sample PDFs for testing
- `processed_output/`: Output directory for processed content
- `test_output/`: Directory for test outputs

3. The dependencies include:
- marker-pdf: PDF processing
- transformers: For Florence-2 model
- torch: Deep learning framework
- Pillow: Image processing
- chromadb: Vector storage

## Key Modules
This repo contains the main branches to be shared with other researchers, like us, or with collaborators who are pursuing similar research questions.

The branches shared here comprise:

1. Simple VLM-RAG mode to understand flattened PDF technical manuals
2. Preparation of the vector store (this uses the `run_pipeline.py`)
3. Eval mode
4. simple multi agent mode with MCP for inventory check agent, web search, and a RAG agent
5. advanced agent mode with more robust query analysis [feature/advanced-rag-functions](https://github.com/simkimsia/genai-202504-team-1/tree/feature/advanced-rag-functions)
6. Query-Answering (this uses the streamlit and output folder and `rag_storage` folder)


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


KeThere are two phases:

1. Preparation of the vector store (this uses the `run_pipeline.py`)
2. Query-Answering (this uses the streamlit and output folder and `rag_storage` folder)

### Common Issues


7. `streamlit run src/modules/query_answering/rag_chat_app.py` to run the chat

### Common Commands

### end to end for preparation

```bash
python run_pipeline.py
    --pdf_path input-pdfs/sample.pdf \
    --output_dir output   \
    --storage_path clip_bm25_docu_summary \
    --image_processor_impl "florence" \
    --embedder_impl "clip" \
    --document_summary='This technical manual provides detailed service and repair instructions for System4 Electronic Fuel Injection (MEFI) equipped engines, emphasizing safety, proper part replacement, and diagnostic procedures.'
```

### preprocessed

```bash
python run_pipeline.py --pre_processed_dir output/sample_20250525_185322 --output_dir output
```

### with document summary

```bash
python run_pipeline.py \
    --pre_processed_dir=output/MEFI-5-Service-Manual_20250610_162940 \
    --storage_path clip_bm25_docu_summary \
    --image_processor_impl "florence" \
    --embedder_impl "clip" \
    --document_summary='This technical manual provides detailed service and repair instructions for System4 Electronic Fuel Injection (MEFI) equipped engines, emphasizing safety, proper part replacement, and diagnostic procedures.'
```

### querying

```bash
streamlit run src/modules/query_answering/rag_chat_app.py
```

