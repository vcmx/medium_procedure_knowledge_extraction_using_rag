# Experimental Components Progress Tracking

This document tracks the progress of implementing and experimenting with different components in our PDF processing system.

## Component Progress Matrix

| Phase                | Component         | Current Choice      | Alternative Options                                   | Key Considerations                                  | Status | What Has Been Tried | Notes |
|----------------------|-------------------|--------------------|------------------------------------------------------|-----------------------------------------------------|--------|-------------------|-------|
| Preparation          | PDF Processing    | Marker             | PyMuPDF, PDFMiner, pdf2image + Tesseract              | Text/image extraction quality, structure, speed     | 🔄 In Progress | [Howard tried PyMuPDF](https://github.com/hclee333/CS614_Qwen_2.5_Shared/blob/4c363651bce407448916ca937e04f74234b995b4/src/document_processor.py#L4), Kimsia tried llamaparse, Howard tried image-based pdf (AIrfix.pdf) as well. Kimsia tried to run marker and pymupdf on the same AIrfix.pdf see results [here](https://www.loom.com/share/869a96a6823e4a579168489f198d8947?sid=1528f937-648e-4a53-901b-ba5fd7649da1) | Howard points out text bleeding into images is an issue with text-based pdf. Kimsia agrees though thinks this issue doesn't occur so much for technical manuals. Waiting Vincent to confirm. [Differences between text-based and image-based pdf](https://medium.com/quantrium-tech/identifying-text-based-and-image-based-pdfs-using-python-10dba29a02b4) |
| Preparation          | Image Captioning  | Florence-2         | BLIP-2, GPT-4V, LLaVA, CogVLM                         | Caption accuracy, technical content, speed, resources| 🔄 In Progress | Shane did a [Florence example](https://github.com/unused1/CS614_Group_Agent/blob/main/notebooks/03_florence2.ipynb) amongst [others](https://github.com/unused1/CS614_Group_Agent/tree/main/notebooks) and Kimsia implemented it on Subaru. Image captioning seems to take 10s per image running on macbook M1 Max 64 Gb ram. May consider moving to cloud-based to be faster. Howard [tried Qwen 2.5 VL model](https://github.com/hclee333/CS614_Qwen_2.5_Shared/blob/4c363651bce407448916ca937e04f74234b995b4/src/embedding_manager.py#L83) via Ollama | |
| Preparation          | Text Embedding    | CLIP               | Sentence Transformers, BERT variants, OpenAI embeddings| Embedding quality, semantic search, speed, cost     | 🔄 In Progress | Howard tried [nomic-embed-text](https://github.com/hclee333/CS614_Qwen_2.5_Shared/blob/4c363651bce407448916ca937e04f74234b995b4/src/embedding_manager.py#L33), Kimsia tried CLIP. CLIP on macbook M1 Max 64 Gb ram can take longer than 10 seconds | |
| Preparation          | Vector Database   | ChromaDB           | Pinecone, Weaviate, Qdrant, Milvus                    | Query performance, scalability, metadata, deployment| 🔄 In Progress |  | |
| Preparation          | Chunking Strategy | Section-based      | Fixed-size, sentence-based, paragraph-based, ML-based  | Context, search relevance, overhead, structure      | 🔄 In Progress | | |
| Preparation          | Image Processing  | Direct storage     | Image compression, thumbnail, feature extraction       | Storage, retrieval speed, quality, resource usage   | 🔄 In Progress | | |
| Querying/Answering   | Query Embedding   | CLIP               | OpenAI embeddings, Sentence Transformers, custom models| Query understanding, cross-modal, speed, cost       | 🔄 In Progress | | |
| Querying/Answering   | Retrieval         | Vector similarity  | Hybrid (BM25+vector), multi-stage, context-aware       | Retrieval accuracy, speed, context, diversity       | 🔄 In Progress | | |
| Querying/Answering   | Reranking         | None               | Cross-encoder, custom rerankers, rule-based            | Result quality, latency, cost                       | 🔄 In Progress |  | |
| Querying/Answering   | Answer Generation | LLM (e.g. GPT-4)   | Llama, Mistral, Claude, custom fine-tuned models       | Answer quality, context window, cost, latency       | 🔄 In Progress | Howard tried [qwen2.5vl:3b](https://github.com/hclee333/CS614_Qwen_2.5_Shared/blob/4c363651bce407448916ca937e04f74234b995b4/src/rag_manager.py#L37) via Ollama as query-answering model, Kimsia tried [meta-llama/llama-4-maverick](https://github.com/simkimsia/genai-202504-team-1/blob/c9dee5d8f55e606d3fe3684cd18a9c4c0552182f/src/modules/query_answering/rag_with_chroma.py#L41) via openrouter | |

## Status Legend
- 🔄 In Progress
- ✅ Completed
- ⏸️ On Hold
- 🚫 Blocked
- 📊 Under Evaluation

## Progress Updates

### Latest Updates
*[Add date and updates here]*

### Key Milestones
*[Add key milestones and achievements here]*

### Challenges and Blockers
*[Add any challenges or blockers here]*

### Next Steps
*[Add next steps and priorities here]*

## Notes
- This document should be updated regularly as progress is made
- Each component's status should be updated with specific details about implementation progress
- Include links to relevant documentation, code, or research as they become available
- The "What Has Been Tried" column should include:
  - Previous approaches attempted
  - Results and learnings from each attempt
  - Reasons for switching to current approach
  - Any A/B test results