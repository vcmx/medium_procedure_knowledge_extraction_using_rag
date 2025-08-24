## Relevant Files

- `src/modules/query_answering/rag_with_chroma.py` - Contains the `MultimodalChromaRAGQueryEngine` which will house the core fusion logic.
- `src/modules/query_answering/rag_chat_app.py` - The Streamlit application UI that needs to be updated with the new search options.
- `src/modules/query_answering/tests/test_rag_with_chroma.py` - Unit tests for the query engine to verify the new fusion logic.

### Notes

- The logic for RRF and Interleaving will be implemented in `rag_with_chroma.py`.
- The `rag_chat_app.py` file will be updated to pass a new parameter to the query engine based on the user's selection.

## Tasks

- [ ] 1.0 Refactor Query Engine to Accept a Fusion Method
  - [x] 1.1 In `rag_with_chroma.py`, change the `query` method signature from `use_hybrid_search: bool` to `fusion_method: Optional[str] = None`.
  - [x] 1.2 Update the conditional logic to check `if fusion_method == 'interleave':` for the existing hybrid search logic.
- [x] 2.0 Implement Reciprocal Rank Fusion (RRF) Logic
  - [x] 2.1 In `rag_with_chroma.py`, add a new `elif fusion_method == 'rrf':` block.
  - [x] 2.2 Inside this block, implement the RRF algorithm: initialize an `rrf_scores` dictionary.
  - [x] 2.3 Loop through both vector and BM25 search results, calculating and accumulating RRF scores for each document based on its rank.
  - [x] 2.4 Sort the unique documents by their final RRF score in descending order to create the final `search_results` list.
- [x] 3.0 Update Streamlit UI with New Hybrid Search Options
  - [x] 3.1 In `rag_chat_app.py`, locate the `st.radio` widget for `search_strategy`.
  - [x] 3.2 Update the `options` parameter with the new list: `["Vector Search Only", "Vector + MMR", "Vector + BM25 (Interleaving)", "Vector + BM25 (RRF)"]`.
- [x] 4.0 Connect UI Selection to Query Engine Backend
  - [x] 4.1 In `rag_chat_app.py`, remove the `use_hybrid_search` boolean variable.
  - [x] 4.2 Add logic to set a `fusion_method` variable to `'interleave'`, `'rrf'`, or `None` based on the `search_strategy` selection.
  - [x] 4.3 Update the call to `st.session_state.query_engine.query` to pass `fusion_method=fusion_method` instead of `use_hybrid_search`.
- [ ] 5.0 End-to-End Testing of New Search Strategies
  - [ ] 5.1 Manually test the "Vector Search Only" option in the UI to ensure it functions as before.
  - [ ] 5.2 Manually test the "Vector + MMR" option to ensure it functions as before.
  - [ ] 5.3 Manually test the "Vector + BM25 (Interleaving)" option and verify it returns fused results.
  - [ ] 5.4 Manually test the "Vector + BM25 (RRF)" option and verify it returns fused results.

## blocked by

- now this list is blocked by [prd integrated agent chat ui](tasks-prd-integrated-agent-chat-ui.md)