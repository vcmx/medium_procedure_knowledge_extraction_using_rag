# RAG for technical manuals

A RAG using streamlit as frontend and CHromaDB as vector store.

Most important two branches are

1. [main](https://github.com/simkimsia/genai-202504-team-1/tree/main) that covers:

   1. preparation of rag phase with `run_pipeline.py`
   2. simple rag mode
   3. eval mode
   4. simple multi agent mode with MCP for inventory check agent, web search, and a RAG agent
2. [feature/advanced-rag-functions](https://github.com/simkimsia/genai-202504-team-1/tree/feature/advanced-rag-functions) that covers:
   1. the advanced agent mode with more robust query analysis.

For more details you can check out the Notion and the Loom videos

## Notion Page with breakdown of RAG components and slide 📝

- [Notion Page with Table public to internet for anyone with link](https://www.notion.so/oppoin/Layers-of-RAG-2025-06-21a891e863f580a381abf976a6f9540d?pvs=4)

## Useful Loom Videos 🎥

- [Preparation Phase](https://www.loom.com/share/23aeb8a522084b3bbbcf0cd0acd24ab3)
- [Simple RAG](https://www.loom.com/share/fd7470540e57449f8fc7448cb3ce4797?sid=bb49e38f-7441-48fb-85d5-a007b9afcbca)
- [Evaluation Mode](https://www.loom.com/share/cdabdc3ba35c4e428ecb70fba90398d4?sid=d7b914fb-534c-472d-8b29-6f0a73b41820)
- [Multi Agent Mode with MCP for Inventory Check, Web Search Agent](https://www.loom.com/share/524d551f51d7486b8a2a42f44ee33bbb?sid=487c1b78-f000-42a6-9942-c641012acdbd)
- [Advanced Agent Mode with More Robust Query Analysis](https://www.loom.com/share/b507586f99994b13812c37c772e9409f?sid=f78d7e62-0600-4345-aa9e-c6af70f75baf)


## Project Structure

```
.
├── setup.py              # Package setup file
├── pyproject.toml        # Modern Python packaging config
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
└── output/         #  output directory holding the processed markdown and images extracted rom PDF
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install the package in development mode:

   ```bash
   pip install -e .
   ```

3. Add a sample PDF to the `input-pdfs` directory for testing.

## Development

There are two phases:

1. Preparation of the vector store (this uses the `run_pipeline.py`)
2. Query-Answering (this uses the streamlit and output folder and `rag_storage` folder)

## Project Organization

- `src/modules/`: Contains all processing modules
  - `pdf_processor/`: PDF processing using Marker
  - (Future modules will be added here)
- `tests/`: Test files
- `input-pdfs/`: Sample PDFs for testing
- `processed_output/`: Output directory for processed content
- `test_output/`: Directory for test outputs

## Dependencies

- marker-pdf: PDF processing
- transformers: For Florence-2 model
- torch: Deep learning framework
- Pillow: Image processing
- chromadb: Vector storage

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'marker'**
   - Make sure you've installed all dependencies: `pip install -e .`
   - Check that marker-pdf is installed: `pip list | grep marker-pdf`

2. **ImportError: cannot import name 'Marker'**
   - The package name is 'marker-pdf', not 'marker'
   - Make sure you're using the correct import: `from marker_pdf import Marker`

## QuickStart for Regular Streamlit

[🎥 Watch this loom!!](https://www.loom.com/share/a2e8abbf85fb4a99b3be74a7e54ebfe1?sid=fadf23c4-fdbe-40f5-afee-f7c116f158b2)

1. Use `main` branch
2. Get your own openrouter API key at <https://openrouter.ai/settings/keys>
3. make a copy of `.env.example` and name the copy as `.env` and put your keys in directly. DO NOT COMMIT `.env` file!! Bad practice!!!
4. create your own virtual env using python 3.12. If you want you can also use conda.
5. Turn on your venv. You may need different venv for different situations:
   1. main branch running preparation
   2. main branch running streamlit
   3. feature/advanced-rag-functions running streamlit
6. Use the appropriate `requirements.txt`
   1. `requirements.txt` is for main branch to run the first 3 modes: simple rag, eval mode, multi agent mode
   2. `requirements-prep.txt` for pipeline processing in main branch
   3. `requirements-query-analysis.txt` for advanced agent mode in `feature/advanced-rag-functions` branch
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

