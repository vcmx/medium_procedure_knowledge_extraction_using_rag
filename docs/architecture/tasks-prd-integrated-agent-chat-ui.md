## Relevant Files

- `src/modules/query_answering/rag_chat_app.py`: The main Streamlit application file that will be heavily modified to incorporate the new agent-based mode and UI logic.
- `src/modules/agent/agent_controller.py`: The controller for the multi-agent system. This will be imported and used in `rag_chat_app.py`, but not modified.
- `tests/ui/test_rag_chat_app.py`: A new test file should be created to add component tests for the new UI modes and logic to prevent regressions.

### Notes

- The implementation will be phased, focusing on integrating functionality into the main `rag_chat_app.py` file.
- State management (`st.session_state`) will be crucial for a clean implementation.
- **Chat History Reset:** It is expected and required that the chat history (`st.session_state.messages`) is cleared whenever a core configuration is changed to prevent inconsistent states. This includes: switching the mode (Simple RAG vs. Multi-Agent), changing the RAG storage selection, and updating the user experience level.
- Unit and component tests should be created or updated to reflect the new functionalities and ensure existing features are not broken.

## Tasks

- [x] **1.0 UI Scaffolding and Mode-Switching Logic**
  - [x] 1.1 In `rag_chat_app.py`, add a `st.radio` button to the sidebar for `"Simple RAG"` and `"Multi-Agent"` modes.
  - [x] 1.2 Store the selected mode in `st.session_state`.
  - [x] 1.3 Refactor the existing UI into a function, e.g., `run_simple_rag_mode()`.
  - [x] 1.4 Create a new placeholder function, e.g., `run_multi_agent_mode()`.
  - [x] 1.5 Add logic to the main app body to call the appropriate function based on the selected mode in `st.session_state`.
  - [x] 1.6 Ensure that switching modes clears the chat history to prevent confusion.

- [x] **2.0 Basic Multi-Agent Mode Integration**
  - [x] 2.1 In `run_multi_agent_mode()`, import the `AgentController`.
  - [x] 2.2 Initialize the `AgentController` once and store it in `st.session_state` to persist it across reruns.
  - [x] 2.3 Design the sidebar for the Multi-Agent mode, hiding the Simple RAG controls and adding the "Experience Level" selector.
  - [x] 2.4 Implement the chat input for the agent mode.
  - [x] 2.5 On receiving a query, call the `agent_controller.process_query()` method. For now, iterate through the generator to get only the final answer and display it.

- [x] **3.0 Visualize Agent Steps in UI**
  - [x] 3.1 Create a new helper function, e.g., `display_agent_step(step)`, that takes an agent step dictionary as input.
  - [x] 3.2 Inside this function, use `st.container` to create a visually distinct block for the agent output.
  - [x] 3.3 Add the agent's name as a title with a corresponding icon and color, as specified in the PRD.
  - [x] 3.4 Modify the query processing loop from task 2.5 to call `display_agent_step()` for each step yielded by the controller, not just the final result.
  - [x] 3.5 Display the Supervisor's routing decision to provide better feedback during agent processing latency.

- [x] **4.0 Refactor for Interactive, Turn-Based Agent Workflow**
  - **Important Constraints for this refactor:**
    - **No Regressions:** All changes must be strictly confined to the `run_multi_agent_mode()` function. The `run_simple_rag_mode()` function and its existing functionality must remain completely unaffected.
    - **Preserve Full History:** The entire clarification exchange (both the agent's questions and the user's answers) must be appended to the chat history (`st.session_state.messages`) so it remains visible on screen throughout the session. Do not wipe or hide this part of the conversation.
  - [x] **Phase 4.1: State Management & Core Logic Refactor**
    - [x] 4.1.1 In `rag_chat_app.py`, introduce new `st.session_state` keys to manage the agent's lifecycle: `agent_generator` (to store the pausable process), `waiting_for_clarification` (as a boolean flag), and `clarification_data` (to hold questions and the original query).
    - [x] 4.1.2 Restructure the `run_multi_agent_mode` function to move the agent processing logic outside the `st.chat_input` block. The new logic will run on every script rerun, processing only one step at a time from the generator stored in `st.session_state.agent_generator`.
    - [x] 4.1.3 After processing each step, immediately render it using the existing `display_agent_step` function to provide real-time visibility into the agent's work.
    - [x] 4.1.4 Within this new loop, detect if a step contains `clarification_needed: True`.

  - [x] **Phase 4.2: Implement Clarification UI and State Handling**
    - [x] 4.2.1 When clarification is detected, set `st.session_state.waiting_for_clarification = True`.
    - [x] 4.2.2 Store the agent's questions and the original user query in `st.session_state.clarification_data`.
    - [x] 4.2.3 Append the agent's clarification questions to the main chat history (`st.session_state.messages`) so they are visibly part of the conversation.
    - [x] 4.2.4 Use `st.form` to conditionally display a clarification form only when `st.session_state.waiting_for_clarification` is `True`. The form should dynamically generate a `st.text_input` for each question.

  - [x] **Phase 4.3: Resuming the Agent Workflow with User Input**
    - [x] 4.3.1 When the clarification form is submitted, capture the user's responses.
    - [x] 4.3.2 Append the user's answers to the chat history (`st.session_state.messages`) to ensure the entire exchange is recorded and visible.
    - [x] 4.3.3 Set `st.session_state.waiting_for_clarification = False`.
    - [x] 4.3.4 Call `agent_controller.process_query()` a second time, passing the original query along with the new `clarification_responses`.
    - [x] 4.3.5 Store the new generator returned by this call in `st.session_state.agent_generator` and trigger an `st.rerun()` to continue the step-by-step processing.

- [ ] **5.0 Finalize, Refactor, and Address Open Questions**
  - [ ] 5.1 Implement a user-friendly error handling mechanism. When the agent controller raises an exception, display a clean error message in the UI (e.g., `st.error`).
  - [ ] 5.2 Add a small section in the sidebar for "Demo Queries" with clickable buttons that automatically populate the chat input with predefined questions from the PRD.
  - [ ] 5.3 Review and refactor the code in `rag_chat_app.py` for clarity, separating UI logic from application logic where possible.
  - [ ] 5.4 Add docstrings and comments to the new functions.
  - [ ] 5.5 Add a check to verify Ollama connection and display a warning if it fails.

- [x] **6.0 Vector Store Integration for Multi-Agent Mode**
  - [x] **6.1 Add RAG Selection UI to Sidebar**: In `rag_chat_app.py`, add a `st.selectbox` to the "Multi-Agent" mode sidebar. This will allow users to choose from a predefined list of available RAG storages (e.g., "CLIP-based RAG", "Qwen-based RAG").
  - [x] **6.2 Define RAG Configuration Mapping**: Create a dictionary to map the user-friendly names from the selectbox to the actual `rag_path` and `embedder_impl` parameters (e.g., `{"CLIP-based RAG": {"path": "./rag_storage/clip_default", "embedder": "clip"}}`).
  - [x] **6.3 Make Simple RAG adopt same configuration**: Make Simple RAG adopt the same setup for storage folder.
  - [x] **6.4 Implement Dynamic `AgentController` Initialization**: Modify the logic in `run_multi_agent_mode` to re-initialize the `AgentController` instance in `st.session_state` whenever the selected RAG storage changes. The new controller must be created with the correct path and embedder from the configuration map.
  - [x] **6.5 Update `AgentController` to Accept RAG Parameters**: Refactor the `AgentController` class in `src/modules/agent/agent_controller.py` to accept `rag_path` and `rag_embedder_impl` during its initialization. This will allow it to dynamically load the specified RAG agent.
  - [x] **6.6 Reset Chat State on RAG Change**: Ensure that when the RAG selection is changed, the multi-agent chat history (`st.session_state.messages`) and the agent session are cleared. Display a `st.toast`

- [x] **8.3 Update `display_agent_step` for `RAGAgent`**: Modify `display_agent_step()` in `rag_chat_app.py`. When the agent is `rag`, it should display the `answer` from the results and then call the new `display_sources()` function to render the detailed, interactive source information.
- [x] **8.4 Remove `_format_response` Method**: Since the UI will now handle all display logic, the `_format_response` method in `RAGAgent` will be obsolete and should be removed.

- [x] **9.0 Implement Context-Aware Clarification**
  - **Goal:** Make the Query Analyzer "smarter" by giving it knowledge of the available documents in the RAG store, enabling it to ask more relevant and targeted clarification questions.
  - [x] **Phase 9.1: Expose Document Metadata**
    - [x] 9.1.1 In `src/modules/query_answering/rag_with_chroma.py`, create a new method in the `MultimodalChromaRAGQueryEngine` class called `get_all_document_summaries()`. This method should efficiently query the ChromaDB store to return a list of unique document titles or summaries.
  - [x] **Phase 9.2: Grant Agent Access to Metadata**
    - [x] 9.2.1 In `src/modules/agent/controller.py`, modify the `AgentController.__init__` method to pass the `rag_agent.query_engine` instance to the `QueryAnalyzerAgent` upon its initialization.
    - [x] 9.2.2 In `src/modules/agent/query_analyzer_agent.py`, update `QueryAnalyzerAgent.__init__` to accept and store this `query_engine` instance.
  - [x] **Phase 9.3: Integrate Context into Clarification Logic**
    - [x] 9.3.1 In `src/modules/query_analyzer/conversation_manager.py`, update the `

- [ ] **10.0 Fix Agentic Loop and Supervisor Logic**
  - [x] **10.1 Refactor the supervisor agent to be purely rule-based, removing the LLM call to prevent feedback loops.**