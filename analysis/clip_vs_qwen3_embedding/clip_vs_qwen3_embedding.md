# Analysis of RAG Pipeline Performance: `CLIP` vs. `Qwen3-Embedding-4B`

**Date:** June 7, 2025

[🎥 Watch the loom](https://www.loom.com/share/cb38417334de4a8985e435de2a919f24?sid=f7ef2d13-0b56-4b70-a1d0-a8fcc4990b9a)

## 1. Executive Summary

This report analyzes a sophisticated multimodal RAG (Retrieval-Augmented Generation) pipeline, comparing the impact of two distinct embedding models: `openai/clip-vit-base-patch32` and `Qwen/Qwen3-Embedding-4B`.

While both models successfully retrieve relevant documents for a given query, the analysis reveals that **`Qwen3-Embedding-4B` provides significantly more precise and actionable results**. This superior retrieval quality enables the downstream Large Language Model (LLM) to generate answers that are not only more accurate but also more confident and structured.

However, this improvement in quality comes with a measurable performance trade-off. On an Apple M1 Max with 64GB RAM, processing a 12-page technical manual with 43 images took approximately **21 minutes with the `Qwen3` pipeline**, compared to **16 minutes with the `CLIP` pipeline**.

The key takeaway is that for high-stakes, text-centric RAG applications like a technical repair assistant, specialized, high-dimension text embedding models like `Qwen3` offer a substantial quality advantage that justifies the additional upfront processing time.

## 2. System Architecture & Data Flow

The RAG pipeline is composed of several best-in-class components, each playing a critical role in the data ingestion process. The flow is as follows:

*(A simple diagram illustrating the flow: PDF -> Marker -> (Text, Images) -> Florence-2 -> (Text, Captions) -> Concatenate -> Embedder -> ChromaDB)*

1. **PDF Parsing (`Marker`):** The process begins with `Marker`, which converts unstructured PDF documents into clean, structured Markdown. This step is crucial as it preserves the document's semantic layout, including headers, lists, and tables, which are vital for contextual understanding.

2. **Image Captioning (`Florence-2`):** As `Marker` extracts text, it also saves images from the PDF. The powerful `microsoft/Florence-2-large` model then processes these images to generate descriptive text captions. This elegantly transforms vital visual information into a textual format that can be processed alongside the main document text.

3. **Chunking Strategy:** An analysis of `src/modules/pipeline/multimodal_rag_pipeline.py` reveals a sophisticated, two-level chunking strategy.
    * **Structural Parsing:** The pipeline first divides the document into large, logical `Sections` based on the headers identified by `Marker` (e.g., "TIMING BELT", "Installation").
    * **Semantic Chunking:** A `TextProcessor` then breaks down the content *within* each of these large sections into smaller, semantically coherent chunks.
    This hierarchical approach is superior to naive fixed-size chunking as it ensures that chunks maintain high contextual relevance and respect the document's inherent structure.

4. **Hybrid Content Creation:** For each section, the pipeline intelligently combines the textual content with the generated captions from all images appearing in that section. This creates a single, rich text block that represents all the information (textual and visual) for that part of the document.

5. **Vector Embedding (`CLIP` or `Qwen3`):** This is the core component under analysis. The combined text block is fed into the chosen embedding model, which converts it into a high-dimensional vector.

6. **Vector Storage (`ChromaDB`):** The resulting vector embeddings and their associated metadata (e.g., page number, section title) are stored in a `ChromaDB` vector store, which is optimized for efficient similarity search and retrieval.

## 3. Analysis of Embedding Models: `CLIP` vs. `Qwen3`

The choice of embedding model has the most significant impact on the quality of the RAG system's output.

### Model Specialization & Pipeline Synergy

* **`CLIP` (`openai/clip-vit-base-patch32`):** A multimodal model optimized for **cross-modal** tasks, i.e., mapping images and text to a shared space. It's a generalist.
* **`Qwen3-Embedding-4B`:** A specialized, state-of-the-art text embedding model. It is built on a powerful LLM foundation and fine-tuned specifically for **text-vs-text** retrieval. It's a specialist.

**Key Insight:** Your pipeline's design, which converts all images to text captions *before* the embedding step, transforms the problem into a pure text-vs-text retrieval task. This architecture perfectly leverages the strengths of the specialist (`Qwen3`) and moves away from the primary use case of the generalist (`CLIP`).

### The Role of Embedding Dimensions

* **`CLIP`:** **512** dimensions
* **`Qwen3-Embedding-4B`:** **2560** dimensions

**Key Insight:** The embedding dimension can be thought of as the "resolution" of the vector representation. With **5 times the dimensions**, `Qwen3` has a vastly larger and more flexible vector space. This allows it to capture incredibly fine-grained details, nuances, and semantic relationships from your rich, combined text content. The result is a more accurate and well-organized "map" of your document's knowledge, which leads to superior retrieval.

### Observed Results

The difference in capability was clear in the query results. For the query "how to remove timing belt":

* **`Qwen3`** retrieved documents that were not only relevant but were in the correct procedural order. The high-quality context allowed the final LLM to generate a confident, step-by-step guide.
* **`CLIP`** retrieved documents that were generally on-topic but less precise. This forced the final LLM to infer a process from a vaguer context, leading to a more hesitant and less reliable answer.

## 4. Performance & The Speed-vs-Quality Trade-off

All performance tests were conducted on an **Apple M1 Max with 64GB RAM** using a 12-page Subaru repair manual containing 43 images.

| Metric | `CLIP` Pipeline | `Qwen3` Pipeline | Analysis |
| :--- | :--- | :--- | :--- |
| **Total Ingestion Time** | **~16 minutes** | **~21 minutes** | The `Qwen3` pipeline took **~31% longer**. |

The increased processing time for `Qwen3` is an expected consequence of its significantly larger model size and the computational cost of generating higher-dimensional vectors.

This presents a classic engineering trade-off: **speed vs. quality**. For an application like a technical manual assistant, where the accuracy of the retrieved information is critical to a successful repair, the **5-minute increase in one-time ingestion cost is a small price to pay for the dramatic improvement in answer quality and user trust.**
