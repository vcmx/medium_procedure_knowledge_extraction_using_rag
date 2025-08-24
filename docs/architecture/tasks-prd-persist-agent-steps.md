## Relevant Files

- `src/modules/query_answering/rag_chat_app.py`: This file contains the core UI logic for the "Multi-Agent" mode and will be the primary target for all state management and display logic changes.
- `tests/ui/test_rag_chat_app.py`: Component tests should be updated or created to verify the new state management logic and ensure the UI behaves as expected.

### Notes

- The core of this task is robustly managing `st.session_state` to handle Streamlit's re-render lifecycle correctly.

## Tasks

- [x] **1.0 Initialize State Management**
  - [x] 1.1 In `rag_chat_app.py`, add `st.session_state.agent_steps = []` to the session state initialization block at the top of the file.

- [x] **2.0 Implement Core Display and Persistence Logic**
  - [x] 2.1 In `run_multi_agent_mode`, just before the `st.chat_input` block, add a loop that iterates through `st.session_state.agent_steps` and calls `display_agent_step()` for each step. This will handle the redrawing of steps on re-renders.
  - [x] 2.2 Inside the `if prompt := st.chat_input(...)` block, add `st.session_state.agent_steps = []` to clear the previous turn's steps when a new query is submitted.
  - [x] 2.3 Inside the `for step in st.session_state.agent_controller.process_query(...)` loop, in addition to calling `display_agent_step(step)`, add `st.session_state.agent_steps.append(step)` to save each step to the state.

- [x] **3.0 Integrate Comprehensive State Reset Triggers**
  - [x] 3.1 In the "Multi-Agent" sidebar, find the "Clear Chat" button's `if` block and add `st.session_state.agent_steps = []` to it.
  - [x] 3.2 In the main `AgentController` initialization block, where the agent is re-initialized after a RAG or experience level change, add `st.session_state.agent_steps = []` to ensure steps are cleared.
  - [x] 3.3 In the main `on_mode_change()` function for the mode selector, add `st.session_state.agent_steps = []` to clear the steps when switching away from "Multi-Agent" mode.