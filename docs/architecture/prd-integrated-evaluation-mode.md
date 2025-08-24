# PRD: Integrated Evaluation Mode in Chat App

## 1. Overview

This document outlines the requirements for integrating the RAG Evaluation Streamlit App (`run_evaluation_app.py`) into the main Technical Manual Chat Assistant (`rag_chat_app.py`) as a new, third "Evaluation" mode. The primary goal is to create a single, unified application for both interactive chat and performance evaluation, while ensuring the stability and integrity of the existing chat functionalities.

## 2. Goals

- **Unified Interface:** Consolidate the chat and evaluation tools into a single Streamlit application, accessible via a mode-switching UI.
- **Seamless Integration:** Add an "Evaluation" mode that provides the full functionality of the standalone evaluation app.
- **Stability and Zero Regression:** The integration must not break, alter, or otherwise interfere with the existing "Simple RAG" and "Multi-Agent" modes. State management must be carefully isolated.
- **UI Consistency:** The new mode's controls in the sidebar should follow the established design patterns of the chat app for a consistent user experience.

## 3. User Stories

- **As a developer, I want to** switch to an "Evaluation" mode from within the main chat app, so that I don't have to run a separate application for testing.
- **As a developer, I want to** use this mode to manage a suite of test cases (add, edit, delete, and save) just as I did in the standalone app.
- **As a developer, I want to** select a specific RAG configuration and LLM, run an evaluation against a chosen test case, and see the detailed results, all within the integrated view.
- **As a developer, I must be confident** that switching to and from the "Evaluation" mode will not clear my chat history or disrupt the state of the other chat modes.

## 4. Functional Requirements

### 4.1. Mode Selection

1.  The main `st.radio` widget in `rag_chat_app.py`'s sidebar must be updated to include a third option: **"Evaluation"**.
2.  Switching to "Evaluation" mode will render the evaluation UI in the main panel.
3.  Switching away from and back to the other modes ("Simple RAG", "Multi-Agent") should preserve their state, including chat history.

### 4.2. State Isolation

1.  The "Evaluation" mode **must not** interact with or modify the `st.session_state.messages` list used by the chat modes. All UI outputs for this mode will be rendered in dedicated `st.container` or `st.expander` elements, not as chat messages.
2.  Session state keys for sidebar controls (like the selected LLM or RAG configuration) must be unique to the evaluation mode to prevent conflicts. For example, use `st.session_state.eval_llm` instead of reusing `st.session_state.selected_llm`.

### 4.3. Sidebar Controls

1.  When "Evaluation" mode is active, the sidebar will display its own set of controls, stylistically consistent with the other modes.
2.  It must include an explicit **"Load RAG and Evaluator"** button. The evaluation system (Query Engine, Evaluator) will only be loaded or reloaded when this button is pressed.
3.  The sidebar will feature selection widgets for **RAG Storage** and **LLM Model**. These should be populated from the same `RAG_CONFIGS` and `llm_options` lists as the other modes to ensure consistency, but must use unique `key`s to manage their state independently.

### 4.4. Main Panel UI

1.  The main panel for the "Evaluation" mode will replicate the user interface from `run_evaluation_app.py`. It will be divided into two primary, collapsible sections.
2.  **Run Evaluation Section:**
    -   A dropdown menu to select a test case from the loaded list.
    -   A "Run Evaluation" button that triggers the evaluation process for the selected test case and LLM.
    -   A display area below the button to render the results, including the generated output, scores for each metric, and justifications. This display will be temporary and show only the results of the last run.
3.  **Test Case Management Section:**
    -   This section will implement the **master-detail view** as defined in `prd-evaluation-app-enhancements.md`.
    -   **Master List (Left):** A selectable list of all test cases. It will include buttons to "Add New Test Case" and "Delete Selected Test Case".
    -   **Detail View (Right):** Displays the `name`, `input`, and `expected_output` for the selected test case. It will also display a tabbed view of all historical `evaluation_results`, organized by LLM.
    -   A **"Save All Changes"** button will persist all edits, additions, deletions, and new evaluation results to the `evaluation_test_cases.json` file.

### 4.5. Data and Loading

1.  The system will continue to use `src/modules/evaluation/evaluation_test_cases.json` as the data source for test cases.
2.  The loading of the `QueryEngine` and `Evaluator` objects into session state will be triggered exclusively by the "Load RAG and Evaluator" button.

## 5. Non-Goals (Out of Scope)

-   Displaying evaluation results inside the chat message stream.
-   Any modifications to the core logic or UI of the "Simple RAG" and "Multi-Agent" modes. They should remain functionally identical.
-   Making the test case file path configurable in the UI.

## 6. Technical Considerations

-   **Code Refactoring:** The UI-building functions from `run_evaluation_app.py` (e.g., `display_evaluation_ui`, `display_test_case_manager`) should be refactored into a single callable function, `run_evaluation_mode()`, within `rag_chat_app.py`. The `main` logic of the old app will be adapted into this function.
-   **State Management:** Strict separation of session state is paramount. A clear naming convention for keys (e.g., prefixing with `eval_`) is recommended to avoid collisions.
-   **Dependencies:** Ensure all necessary dependencies from `run_evaluation_app.py` are accounted for in the main application's environment.

## 7. Success Metrics

-   The "Evaluation" mode is selectable and fully functional within `rag_chat_app.py`.
-   All features from the standalone evaluation app (running tests, managing cases, saving results) work correctly in the integrated mode.
-   The "Simple RAG" and "Multi-Agent" modes are unaffected and continue to function as expected, with their chat histories preserved across mode switches.
-   The application feels cohesive, with consistent UI patterns across all three modes.