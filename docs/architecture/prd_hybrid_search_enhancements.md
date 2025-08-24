# PRD: Enhanced Hybrid Search and Contextualization

**Status:** Proposed
**Date:** 2025-06-15
**Author:** Kimsia
**Editor:** AI Assistant

## 1. Overview

This document outlines the requirements for significantly enhancing the RAG system's retrieval capabilities. The proposed changes include:

1. **Advanced Search Strategies:** Transitioning from a simple MMR checkbox to a comprehensive set of mutually exclusive search options, including "Vector Search Only", "Vector + MMR", "Vector + BM25 (Interleaving)", and a new "Vector + BM25 (RRF)" method.
2. **Expanded Retrieval Scope:** Increasing the configurable number of retrieved documents from a maximum of 10 to 20, with the default changing from 5 to 10.
3. **Enhanced Context:** Augmenting each retrieved text chunk with a summary of its source document to provide better context and aid in differentiating between similar concepts from various sources.

## 2. Problem Statement

The current RAG system has several limitations that hinder retrieval effectiveness and user experience:

- **Inflexible Search Options:** The use of a boolean checkbox for MMR is restrictive. It prevents the combination of different retrieval strategies and does not support more advanced fusion techniques like Reciprocal Rank Fusion (RRF).
- **Limited Retrieval-K:** The upper limit of 10 documents for retrieval is insufficient for complex queries that require a broader context.
- **Lack of Context:** Retrieved text chunks are presented without the broader context of their source document. This makes it difficult for users to differentiate between similar chunks from different documents, reducing the quality of the synthesized answer.

## 3. Goals and Objectives

- **Improve Retrieval Accuracy:** Introduce RRF as a state-of-the-art fusion method and provide document-level summaries to generate more relevant and context-aware answers.
- **Enhance User Control:** Empower users with more granular control over the search strategy and the number of documents to retrieve.
- **Increase UI Clarity:** Replace the MMR checkbox with a clear, radio-button-based selection of distinct search strategies.
- **Provide Deeper Context:** Include document-level summaries with each retrieved chunk to improve comprehension.

## 4. User Stories

- As a user, I want to choose from a clear list of search strategies (Vector only, MMR, Interleaving, RRF) so that I can select the best method for my query.
- As a user, I want to be able to retrieve up to 20 text chunks, with a default of 10, so that I can get a more comprehensive context for my query.
- As a user, I want to see a summary of the source document for each retrieved text chunk so that I can quickly understand its context and relevance.

## 5. Requirements

### Functional Requirements

1. The UI must replace the MMR checkbox with a radio button selector for the search strategy, offering the following options:
    - `Vector Search Only`
    - `Vector + MMR`
    - `Vector + BM25 (Interleaving)`
    - `Vector + BM25 (RRF)`
2. The UI must include a slider to select the number of results to retrieve (`top_k`), with a range of 1 to 20 and a default value of 10.
3. The query engine must implement the Reciprocal Rank Fusion (RRF) algorithm.
4. For each retrieved text chunk, the system must also retrieve and display a summary of its source document.
5. The query engine must be updated to accept the chosen search strategy and `top_k` value from the UI and execute the query accordingly.

### Non-Functional Requirements

1. The performance overhead of the RRF calculation and document summary retrieval should be minimal and not noticeably impact the query response time.

## 6. Technical Implementation Details

- **`src/modules/query_answering/rag_chat_app.py`**:
  - Replace the `st.checkbox` for MMR with a `st.radio` widget for `search_strategy` with the new list of options.
  - Add a `st.slider` to control the `top_k` value.
  - The call to `query_engine.query` will be updated to pass the selected search strategy and `top_k` value.
  - The UI will be updated to display the document-level summary alongside each retrieved text chunk.
- **`src/modules/query_answering/rag_with_chroma.py`**:
  - The `query` method signature in `MultimodalChromaRAGQueryEngine` will be updated to accept `search_strategy: str` and `top_k: int`.
  - The query logic will be refactored to handle the four different search strategies.
  - The RRF logic will be implemented to re-rank the combined BM25 and vector search results.
  - The retrieval process must be updated to fetch document-level summaries stored as metadata alongside the text chunks in ChromaDB.
