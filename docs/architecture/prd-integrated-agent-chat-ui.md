# PRD: Integrated Agent Chat UI

## 1. Introduction/Overview

This document outlines the requirements for integrating the multi-agent system from `interactive_agent_demo.py` into the existing Streamlit-based `rag_chat_app.py`. The goal is to create a single, unified application that can operate in two distinct modes: a "Simple RAG" mode (preserving current functionality) and a "Multi-Agent" mode.

This integration will serve as a proof-of-concept for a class presentation, demonstrating the evolution from a standard RAG pipeline to a more complex, agentic system. The primary user persona is a non-technical user who needs to retrieve information from technical manuals.

## 2. Goals

* Create a single Streamlit interface with a top-level control (e.g., radio button) to switch between "Simple RAG" and "Multi-Agent" modes.
* Preserve all existing functionality of the `rag_chat_app.py` in the "Simple RAG" mode without any breaking changes.
* Translate the command-line interactions of the multi-agent system into an intuitive graphical user interface.
* Clearly visualize the step-by-step reasoning process of the multi-agent system to showcase its inner workings for the presentation.
* Implement the integration in phases to ensure stability at each step.

## 3. User Stories

* **As a presenter**, I want to toggle between a "Simple RAG" mode and a "Multi-Agent" mode within the same app to easily demonstrate and compare their responses to the same query during my presentation.
* **As a non-technical user**, I want to interact with a chat interface that feels intuitive, regardless of the underlying mode.
* **As a presenter**, in "Multi-Agent" mode, I want the UI to clearly show the distinct outputs from each agent (e.g., Supervisor, Query Analyzer) to help my audience understand the decision-making process.
* **As a user**, when the multi-agent system requires more information, I want to be presented with a simple form to provide my answers directly within the chat UI, rather than using a command line.

## 4. Functional Requirements

### FR1: Mode Selection

* The application must feature a high-level UI control (e.g., a `st.radio` button) in the sidebar to select the operational mode: "Simple RAG" or "Multi-Agent".
* The default mode upon application start shall be "Simple RAG".
* Switching the mode should reset the chat history to avoid confusion between modes.

### FR2: Simple RAG Mode

* When "Simple RAG" mode is selected, the application's functionality must be identical to the current `rag_chat_app.py`.
* All existing UI controls (RAG path, embedder, filters, LLM selection, etc.) should function as they currently do.
* No features from the multi-agent system should be active or visible in this mode.

### FR3: Multi-Agent Mode - Core UI

* When "Multi-Agent" mode is selected, the main chat interface will be used for submitting queries.
* The existing sidebar configuration for RAG source and filters should be hidden or disabled, as the agent system manages its own tools and data sources.
* The sidebar should present agent-specific configurations (e.g., user expertise level: NOVICE, EXPERIENCED, EXPERT).

### FR4: Multi-Agent Mode - Visualizing Agent Steps

* When a query is processed, the output from each agent in the workflow (e.g., Supervisor, Query Analyzer, RAG Agent) must be displayed sequentially in the chat area.
* Each agent's output must be visually distinct, using a combination of a unique icon, a background color, and a clear title (e.g., `🤖 SUPERVISOR AGENT:`).
* The final answer should be presented clearly as the concluding message.

### FR5: Multi-Agent Mode - Clarification Workflow

* If the `Query Analyzer` agent determines clarification is needed, the system must not proceed.
* Instead, the UI must display the clarification questions within the chat area.
* Below the questions, a simple form with text inputs should appear, allowing the user to provide answers.
* A "Submit Clarification" button will send the responses back to the agent controller to continue processing.

## 5. Non-Goals (Out of Scope for Initial Phase)

* **Full CLI Command Parity:** We will not implement UI equivalents for *all* CLI commands from `interactive_agent_demo.py` in the first phase. The initial focus is on the `query` workflow. Commands like `session list`, `session switch`, and `status` can be added in later phases.
* **Complex Session Management:** While the agent controller supports multiple sessions, the initial UI will manage only a single, continuous session for the multi-agent mode.
* **Agent Configuration from UI:** The configuration of which agents are available (RAG, MCP, Search) will be hard-coded initially and not selectable from the UI.

## 6. Design Considerations

* **Mode Selector:** Use `st.radio` in the sidebar for clear, immediate mode switching.
* **Agent Step Display:** Use `st.container` with a specific background color and an `st.expander` for each agent's output. This keeps the main chat clean while allowing users to inspect the details of each step.
  * **Supervisor:** Cyan color, 🧠 icon.
  * **Query Analyzer:** Green color, 🔍 icon.
  * **RAG Agent:** Yellow color, 📚 icon.
  * **Final Answer:** No special color, standard assistant message.
* **Clarification Form:** When clarification is needed, display the questions as markdown text and use `st.form` to group the `st.text_input` fields and the submit button. This prevents the app from re-rendering on every keypress.

## 7. Technical Considerations

* **State Management:** Streamlit's session state (`st.session_state`) will be critical for managing the current mode, the `AgentController` instance, and the chat history for each mode.
* **Controller Lifecycle:** The `AgentController` should be initialized once and stored in `st.session_state` when the user first switches to "Multi-Agent" mode.
* **Phased Integration:** The integration should be done in stages to minimize risk.
    1. **Stage 1: UI Scaffolding.** Add the radio button and structure the UI to switch between the two app layouts. Ensure the Simple RAG mode is unaffected.
    2. **Stage 2: Agent Query.** Implement the basic query flow for the agent mode, displaying the final answer without showing intermediate steps.
    3. **Stage 3: Visualize Steps.** Add the detailed, color-coded visualization for each agent's output.
    4. **Stage 4: Clarification Flow.** Implement the UI form for handling clarification questions.

## 8. Success Metrics

* The application successfully runs and operates in both "Simple RAG" and "Multi-Agent" modes.
* Existing functionality in "Simple RAG" mode remains 100% intact and operational.
* The "Multi-Agent" mode correctly processes a query through the agent chain and displays the final result.
* A presenter can clearly articulate the agent workflow to an audience using the visual cues in the UI.

## 9. Open Questions

* How should errors from the agent system be displayed to the non-technical user? Should we show a generic friendly error or the technical details?
* Should the "demo" queries from `interactive_agent_demo.py` be presented as clickable buttons for easy execution in the UI?
