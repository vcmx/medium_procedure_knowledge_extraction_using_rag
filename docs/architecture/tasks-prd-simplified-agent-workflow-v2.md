## Relevant Files

- `src/modules/agent/query_classifier_agent.py` - The new agent to classify user queries.
- `src/modules/agent/web_search_agent.py` - The new agent for performing web searches on general queries.
- `src/modules/agent/simple_supervisor_agent.py` - Will be modified to incorporate the V2 workflow logic.
- `src/modules/agent/simple_controller.py` - May require modifications to handle the new V2 workflow states.
- `src/modules/query_answering/rag_chat_app.py` - The Streamlit UI will be updated to handle the web search results and V2 agent steps.
- `tests/agent/test_query_classifier_agent.py` - Unit tests for the Query Classifier Agent.
- `tests/agent/test_web_search_agent.py` - Unit tests for the Web Search Agent.
- `tests/agent/test_simple_supervisor_agent.py` - Update tests for the V2 supervisor logic.

### Notes

- It is imperative that the existing V1 workflow continues to function perfectly without any regressions.
- The V1 workflow corresponds to the "technical query" path in the V2 diagram.
- All new agents should be created from scratch.

## Tasks

- [x] 1.0 Implement New V2 Agents
  - [x] 1.1 Create the file for the query classifier: `src/modules/agent/query_classifier_agent.py`.
  - [x] 1.2 Implement the `QueryClassifierAgent` class. It must have a `process` method that takes a query and returns a `query_type` of either `general` or `technical`.
  - [x] 1.3 Create the file for the web searcher: `src/modules/agent/web_search_agent.py`.
  - [x] 1.4 Implement the `WebSearchAgent` class with a `process` method that accepts a query and returns formatted web search results.
  - [x] 1.5 Create the corresponding unit test file: `tests/agent/test_query_classifier_agent.py`.
  - [x] 1.6 Write unit tests to verify the classifier correctly identifies both "general" and "technical" queries.
  - [x] 1.7 Create the corresponding unit test file: `tests/agent/test_web_search_agent.py`.
  - [x] 1.8 Write a unit test to ensure the web search agent returns results in the expected format.

- [x] 2.0 Update Supervisor to Orchestrate V2 Workflow
  - [x] 2.1 In `src/modules/agent/simple_supervisor_agent.py`, add `QueryClassifierAgent` and `WebSearchAgent` to the supervisor's initial setup.
  - [x] 2.2 Modify the `process_query` method to first call the `QueryClassifierAgent`.
  - [x] 2.3 Add conditional logic based on the `query_type`.
  - [x] 2.4 If `query_type` is `general`, the supervisor should call the `WebSearchAgent` and yield a new state (e.g., `{'status': 'web_search_complete', 'results': ...}`).
  - [x] 2.5 If `query_type` is `technical`, the supervisor should proceed with the existing V1 workflow (calling `ActionExtractorAgent`, etc.).
  - [x] 2.6 Ensure the output of the `QueryClassifierAgent` is yielded first so it can be displayed in the UI.

- [x] 3.0 Refactor Agent Controller for V2 Logic
  - [x] 3.1 Review `src/modules/agent/simple_controller.py` to ensure it can handle the new state from the supervisor without modification.
  - [x] 3.2 The primary goal is to confirm that the controller's existing loop passes the new `web_search_complete` state to the UI correctly. No code changes are expected, but this verification is a required step.

- [x] 4.0 Adapt Streamlit UI for the V2 Workflow
  - [x] 4.1 In `src/modules/query_answering/rag_chat_app.py`, update the agent processing loop in `run_multi_agent_mode`.
  - [x] 4.2 Add a condition to check for the `web_search_complete` status.
  - [x] 4.3 When this status is received, display the web search results in a user-friendly format and conclude the agent run for that query.
  - [x] 4.4 Update the "View Agent Workflow" expander to always show the result from `QueryClassifierAgent` as the first step.
  - [x] 4.5 Ensure the UI for the V1 technical path (including manual clarification) remains unchanged and fully functional.

- [ ] 5.0 Implement Regression and V2-Specific Testing
  - [x] 5.1 Update `tests/agent/test_simple_supervisor_agent.py` with new test cases for the V2 workflow.
  - [x] 5.2 Add a test that provides a general query and asserts that the `WebSearchAgent` is called.
  - [x] 5.3 Add a test that provides a technical query and asserts that the V1 flow (`ActionExtractorAgent`) is initiated.
  - [x] 5.4 Perform a manual, end-to-end test in the Streamlit app for a general query (e.g., "what is a timing belt?").
  - [x] 5.5 Perform a manual, end-to-end test for a technical query that requires clarification (e.g., "how to remove timing belt") to ensure the V1 clarification flow is not broken.
  - [x] 5.6 Manually verify that the "Simple RAG" mode works as expected to confirm no cross-feature regressions were introduced.