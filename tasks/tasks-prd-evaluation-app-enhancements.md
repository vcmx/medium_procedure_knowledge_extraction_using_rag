## Relevant Files

- `run_evaluation_app.py` - Main Streamlit application file to be modified for UI, data handling, and evaluation logic.
- `src/modules/evaluation/evaluation_test_cases.json` - The JSON file where test cases and their results are stored.
- `src/modules/query/engine.py` - May require updates to the `query` method to accept the selected LLM model.
- `src/modules/evaluation/evaluator.py` - May require updates to the `evaluate` method to use the `expected_output` for more accurate scoring.

### Notes

- Start by updating the `evaluation_test_cases.json` with one example case in the new format to guide development.
- The UI changes for the master-detail view will require careful use of Streamlit's session state to manage the currently selected item.

## Tasks

- [x] 1.0 Update Data Models and I/O for New Test Case Structure
  - [x] 1.1 Modify `load_test_cases` in `run_evaluation_app.py` to be compatible with the new JSON structure (including `expected_output` and `evaluation_results`).
  - [x] 1.2 Modify `save_test_cases` in `run_evaluation_app.py` to correctly write the new complex structure back to the JSON file.
  - [x] 1.3 Manually add one sample test case to `evaluation_test_cases.json` using the new format for initial testing.
- [x] 2.0 Add LLM Selection Feature to UI
  - [x] 2.1 In `run_evaluation_app.py`, add an `st.selectbox` in the sidebar to allow users to choose an LLM.
  - [x] 2.2 Store the user's LLM selection in `st.session_state`.
- [x] 3.0 Modify Core Evaluation Logic
  - [x] 3.1 In `run_evaluation_app.py`, update the "Run Evaluation" logic to use the LLM selected in the sidebar.
  - [x] 3.2 Pass the selected LLM name to the `query_engine.query()` method.
  - [x] 3.3 Update the `LLMTestCase` creation to include the `expected_output` field from the test case.
- [x] 4.0 Fix `embedder_kwargs` TypeError on RAG Loading
  - [x] 4.1 Analyze `QueryEngine.__init__` in `src/modules/query/engine.py` to see how it initializes `MultimodalChromaRAGQueryEngine`.
  - [x] 4.2 Analyze `MultimodalChromaRAGQueryEngine.__init__` in `src/modules/query_answering/rag_with_chroma.py` to identify its correct parameters.
  - [x] 4.3 Modify the `QueryEngine.__init__` method to pass the correct arguments to `MultimodalChromaRAGQueryEngine`, removing `embedder_kwargs`.
- [x] 5.0 Fix OpenAI Authentication Error in DeepEval
  - [x] 5.1 Analyze `src/modules/evaluation/evaluator.py` to confirm how `deepeval` loads API keys (likely from environment variables).
  - [x] 5.2 Add `load_dotenv(override=True)` to the top of `run_evaluation_app.py` to ensure all necessary API keys are loaded into the environment before the evaluator is used.
- [x] 6.0 Fix TypeError in Score Calculation
  - [x] 6.1 **Error Analysis**: The traceback shows a `TypeError` on the line `total_score += score`. This happens because `deepeval` can return a `score` of `None` if it encounters an internal error during evaluation (like the previous API key issue, or if the LLM response is malformed). The current code does not check for this `None` value before trying to perform addition.
  - [x] 6.2 **Solution**: Modify the loop in `display_evaluation_ui` in `run_evaluation_app.py`. Before adding the score to the total, check if it is `None`. If it is, treat it as `0.0` for the calculation and display it appropriately in the UI.
- [x] 7.0 Improve Error Handling in Evaluator
  - [x] 7.1 Modify the `evaluate` method in `src/modules/evaluation/evaluator.py` to wrap the `assert_test` call in a more comprehensive `try...except Exception` block.
  - [x] 7.2 In the `except` block, catch the exception `e` and set the `reason` for the failure to a descriptive string containing the error message (e.g., `f"Evaluation failed: {e}"`), while keeping the `score` as `None`.
- [x] 8.0 Force a Specific Evaluation Model in DeepEval
  - [x] 8.1 Modify the `GEval` constructor in `src/modules/evaluation/evaluator.py` to explicitly use a powerful model (e.g., `gpt-4-turbo`) for evaluation.
- [x] 9.0 Refine DeepEval Error Handling
  - [x] 9.1 **Analysis**: The `AssertionError` from `deepeval` is expected when a score is below the threshold. The error message itself contains the score and reason. Our code should extract this information instead of treating it as a fatal error. The remaining `None` scores are likely due to the complexity of the criteria.
  - [x] 9.2 **Solution**: Modify the `try...except` block in `evaluator.py`. Specifically catch `AssertionError` and, within that block, assign `metric.score` and `metric.reason` to the local variables. This ensures we capture low scores correctly. The general `except Exception` will remain to catch other unexpected errors.
- [x] 10.0 Parse Score and Reason from DeepEval's AssertionError
  - [x] 10.1 **Analysis**: The `AssertionError` from `deepeval` contains the score and reason within its message string. The `metric.score` attribute remains `None`. The correct approach is to parse the error message string itself.
  - [x] 10.2 **Solution**: Modify the `except AssertionError as e:` block in `evaluator.py`. Use the `re` module to parse the `score` and `reason` directly from the `str(e)`. This provides a reliable way to capture results even when the test fails its assertion.
- [x] 11.0 Rebuild Test Case Management UI as Master-Detail View
  - [x] 11.1 In `run_evaluation_app.py`, replace the existing `st.data_editor` in `display_test_case_manager` with a master list of test cases.
  - [x] 11.2 Implement a detail view that appears when a test case is selected from the master list.
  - [x] 11.3 The detail view must display `input`, `expected_output`, and the nested `evaluation_results` for each LLM. Use tabs or expanders for clarity.
  - [x] 11.4 Ensure "Add New" and "Delete" functionality works with the new master-detail layout.
- [x] 12.0 Implement Save/Update Functionality for Evaluation Results
  - [x] 12.1 After an evaluation run, programmatically update the `st.session_state.test_cases` list with the results (`actual_output`, `scores`, timestamp) for the specific LLM used.
  - [x] 12.2 Ensure the "Save Changes" button in the management UI correctly saves the updated session state to `evaluation_test_cases.json`.