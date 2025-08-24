## Relevant Files

- `src/modules/query_answering/rag_chat_app.py` - This is the main application file where the "Evaluation" mode will be integrated.
- `run_evaluation_app.py` - The standalone evaluation app that will be refactored and its code migrated into `rag_chat_app.py`. This file will be deleted after the migration is complete.
- `src/modules/evaluation/evaluation_test_cases.json` - The JSON file containing test cases; its structure will be leveraged by the new mode.
- `tests/query_answering/test_rag_chat_app.py` - A new or existing file for adding tests to ensure the integration does not break existing chat functionality and that the new mode works as expected.

### Notes

- The primary focus is refactoring and integrating existing logic. Ensure that all state management for the new "Evaluation" mode uses unique session state keys (e.g., `eval_*`) to prevent conflicts with the chat modes.
- After successfully migrating all functionality, `run_evaluation_app.py` should be deleted to avoid confusion.

## Tasks

- [x] 1.0 Setup Evaluation Mode Structure in Chat App
  - [x] 1.1 Add "Evaluation" as a new option to the `st.radio` widget for mode selection in the sidebar.
  - [x] 1.2 Create a new function `run_evaluation_mode()` within `rag_chat_app.py` that will be called when the "Evaluation" mode is active.
  - [x] 1.3 Update the main application logic to call `run_evaluation_mode()` when `st.session_state.mode == "Evaluation"`.

- [x] 2.0 Refactor and Migrate Core Logic from Standalone App
  - [x] 2.1 Copy the helper functions `load_test_cases` and `save_test_cases` from `run_evaluation_app.py` into `rag_chat_app.py`.
  - [x] 2.2 Copy the UI functions `display_evaluation_ui` and `display_test_case_manager` into `rag_chat_app.py`.
  - [x] 2.3 Modify the copied functions to accept `st.session_state` as an argument to facilitate isolated state management.

- [x] 3.0 Implement Isolated State Management for Evaluation Mode
  - [x] 3.1 Initialize all necessary session state keys for the evaluation mode upon startup, using unique prefixes (e.g., `eval_test_cases`, `eval_query_engine`, `eval_selected_llm`).
  - [x] 3.2 In `run_evaluation_mode`, create the sidebar controls (RAG selection, LLM selection, "Load RAG and Evaluator" button) using the new, uniquely-keyed session state variables.
  - [x] 3.3 Ensure the "Load RAG and Evaluator" button populates the `eval_` prefixed session state keys, leaving the original chat state keys untouched.

- [x] 4.0 Build Evaluation Mode UI in Main Panel
  - [x] 4.1 make number of results retrieve follow simple rag mode
  - [x] 4.2 follow simple rag mode to have search strategy
  - [x] 4.3 remove filters for page and title
  - [x] 4.4 follow simple rag mode on experience
  - [x] 4.5 follow simple rag mode on llm model
  - [x] 4.6 Within `run_evaluation_mode`, call the refactored `display_evaluation_ui` and `display_test_case_manager` functions.
  - [x] 4.7 Pass the correctly isolated `st.session_state` object or relevant sub-state to these UI functions.
  - [x] 4.8 Verify that the master-detail view for test case management and the "Run Evaluation" panel render correctly without interfering with the chat UI.
  - [x] 4.9 Make previous eval results in detail view follow the same params:
    - [x] 4.9.1 by rag storage options as stated in the sidebar as the first level
    - [x] 4.9.2 by search strategy as stated in the side bar as these second level
    - [x] 4.9.3 by llm model as stated in the side bar as the 3rd level

- [x] 5.0 improve the width layout in all 3 modes

- [ ] 6.0 Finalize Integration and Cleanup
  - [x] 6.1 Thoroughly test the "Evaluation" mode to ensure all features (loading, running, managing, saving) work as expected.
  - [x] 6.2 Add in RAGAS as seen in `evaluate_with_ragas` in `evaluator.py`
    - [x] 6.2.1 try to understand if `evaluate_with_ragas` is superset of `evaluate`. **Analysis:** No, they are complementary. `evaluate` assesses the quality of the final answer, while `evaluate_with_ragas` assesses the RAG pipeline's mechanics (retrieval and grounding).
    - [x] 6.2.2 then decide how to incorporate the scores from `evaluate_with_ragas`. **Decision:** Incorporate RAGAS scores alongside the existing DeepEval scores to provide a more holistic evaluation.
    - [x] 6.2.3 In `src/modules/evaluation/evaluator.py`, create a new method `run_full_evaluation` that accepts an `LLMTestCase` and the list of retrieved `contexts`. This method will call both `evaluate()` and `evaluate_with_ragas()` and return a single, merged dictionary of all scores.
    - [x] 6.2.4 In `src/modules/query_answering/rag_chat_app.py`, modify the "Run Evaluation" logic to capture the `contexts` (retrieved source documents) from the `query_engine.query()` result.
    - [x] 6.2.5 Update the call in `rag_chat_app.py` to use the new `evaluator.run_full_evaluation()` method, passing all required arguments.
    - [x] 6.2.6 Update `eval_display_evaluation_ui` in `rag_chat_app.py` to correctly display both the DeepEval scores and the new RAGAS scores (`faithfulness`, `answer_relevancy`, `context_precision`).
  - [ ] 6.3 Test the "Simple RAG" and "Multi-Agent" modes to confirm they are completely unaffected by the new mode. Ensure chat history is preserved when switching between modes.
  - [ ] 6.4 Delete the original `run_evaluation_app.py` file from the project.
  - [ ] 6.5 Add a new test case to `tests/query_answering/test_rag_chat_app.py` to check for state isolation between modes.

- [x] 7.0 Improve UI for Displaying Evaluation Results
  - [x] 7.1 In `eval_display_evaluation_ui`, split the `evaluation_results` dictionary into two separate dictionaries: one for DeepEval metrics and one for RAGAS metrics.
  - [x] 7.2 Create a new subheader "Answer Quality Assessment" to display the DeepEval metrics, preserving the existing format with detailed expanders for justifications.
  - [x] 7.3 Create a new subheader "RAG Pipeline Performance" to display the RAGAS metrics in a compact, multi-column layout using `st.metric`.
  - [x] 7.4 Add a tooltip or an `st.info` box to the "RAG Pipeline Performance" section to briefly explain what each metric (faithfulness, answer_relevancy, context_precision) measures.

- [x] 8.0 Add "Re-run Evaluation" Button for Faster Debugging
  - [x] 8.1 Add a new button, "Run Eval on Last Known Output," to the UI, positioned next to the original "Run Evaluation" button.
  - [x] 8.2 In `eval_display_evaluation_ui`, modify the result-saving logic to also persist the `retrieved_contexts` from the RAG query alongside the `actual_output`.
  - [x] 8.3 Implement the logic to enable this new button only when the main "Run Evaluation" button is enabled AND a previously saved `actual_output` and `retrieved_contexts` exist for the current test configuration.
  - [x] 8.4 Implement the button's functionality to execute `run_full_evaluation` using the stored data and update the UI and test case file with the new results.
  - [x] 8.5 In `evaluator.py`, modify `run_full_evaluation` to accept `run_deepeval: bool = True` and `run_ragas: bool = True` parameters to conditionally execute each evaluation suite.