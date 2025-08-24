# PRD: Persist Intermediate Agent Steps in UI

## 1. Introduction/Overview

Currently, when the multi-agent system processes a query, the visual outputs from intermediate agents (like the Supervisor and Query Analyzer) disappear from the UI once the final answer is rendered. This prevents users from reviewing the full reasoning chain that led to the result.

This document outlines the requirements to fix this bug by temporarily persisting the visual steps of the most recently executed agent workflow, ensuring they remain on-screen for review.

## 2. Goals

* Ensure all intermediate agent steps from a single query remain visible after the final answer is rendered.
* Improve the user experience by providing a complete, scrollable transcript of the agent's decision-making process for the most recent turn.
* Implement a state management solution that is robust to Streamlit's re-render lifecycle.

## 3. User Stories

* **As a presenter**, I want to scroll up after an answer is generated to show my audience the full sequence of agent steps without them disappearing.
* **As a developer**, I want to inspect the output of every agent in a single turn without having to re-run the query to debug the agent's behavior.
* **As a user**, I want a clean slate when I start a new interaction, so the old intermediate steps should vanish when I clear the chat or change fundamental settings like the knowledge base.

## 4. Functional Requirements

* **FR1: Temporary State Storage:** The application must introduce a new list in `st.session_state` (e.g., `st.session_state.agent_steps`) to store the data for each intermediate agent step of a single query turn.
* **FR2: State Clearing on New Query:** When a user submits a new query in "Multi-Agent" mode, the `st.session_state.agent_steps` list must be cleared before the new agent workflow begins.
* **FR3: Populating State During Processing:** As the `AgentController` yields each step of the workflow, the application must both display the step immediately and append the step's data object to the `st.session_state.agent_steps` list.
* **FR4: Redrawing from State:** The main UI loop must be modified to read from `st.session_state.agent_steps` and redraw all contained steps on every Streamlit re-render.
* **FR5: Comprehensive State Reset:** The `st.session_state.agent_steps` list must be cleared whenever the main chat history is cleared. This includes the following events:
  * The user clicks the "Clear Chat" button.
  * The user changes the selected "RAG Storage".
  * The user changes the selected "Experience Level".
  * The user switches the application mode from "Multi-Agent" to "Simple RAG".

## 5. Non-Goals (Out of Scope)

* Intermediate steps will **not** be persisted across a full browser page reload. They are considered temporary state for the current session view only.
* The UI will **not** provide a history of intermediate steps from *previous* queries (only the most recent one).

## 6. Design Considerations

* The existing visual design for an agent step (a bordered container with an icon, title, and an optional expander for details) is sufficient and should be used for redrawing the steps. No new UI design is required.

## 7. Technical Considerations

* The implementation will primarily affect the logic within `run_multi_agent_mode()` in `src/modules/query_answering/rag_chat_app.py`.
* The core of the fix will involve correctly using `st.session_state` to manage the list of agent steps.

## 8. Success Metrics

* After a multi-agent query completes, all intermediate steps generated during that query remain visible on the screen.
* Executing a new query correctly replaces the previous set of intermediate steps with the new set.
* Changing the RAG model, experience level, or clicking "Clear Chat" successfully removes all intermediate steps from the UI.

## 9. Open Questions

* None at this time.
