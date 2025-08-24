import json
import logging
import os
from datetime import datetime

import streamlit as st
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv

from src.modules.evaluation.evaluator import Evaluator
from src.modules.query.engine import QueryEngine
from src.modules.utils.logging_setup import setup_logging

# Load environment variables from .env file
load_dotenv(override=True)

# --- Configure Logging ---
setup_logging(log_level=logging.DEBUG, app_name="evaluation_app")

# --- Page Configuration ---
st.set_page_config(
    page_title="RAG Evaluation Assistant",
    layout="wide",
)


# --- State Management ---
def get_session_state():
    """Initialize or get the session state."""
    if "test_cases" not in st.session_state:
        st.session_state.test_cases = []
    if "selected_test_case_name" not in st.session_state:
        st.session_state.selected_test_case_name = None
    if "query_engine" not in st.session_state:
        st.session_state.query_engine = None
    if "evaluator" not in st.session_state:
        st.session_state.evaluator = None
    # For master-detail view in test case management
    if "selected_test_case_index" not in st.session_state:
        st.session_state.selected_test_case_index = (
            0 if st.session_state.get("test_cases") else None
        )
    return st.session_state


# --- Data Loading & Saving ---
def load_test_cases(filepath: str) -> list[dict]:
    """Load test cases from a JSON file, ensuring keys for new structure exist."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            test_cases = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Failed to load or parse test cases from '{filepath}': {e}")
        return []

    # Ensure all test cases have the necessary keys for backward compatibility
    for case in test_cases:
        case.setdefault("expected_output", "")
        # Ensure 'evaluation_results' is a dictionary.
        # If it exists but is not a dict (e.g., from an old format), reset it.
        if not isinstance(case.get("evaluation_results"), dict):
            case["evaluation_results"] = {}

    return test_cases


def save_test_cases(filepath: str, test_cases: list[dict]):
    """Save test cases to a JSON file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(test_cases, f, indent=4)
        st.success(f"Test cases saved successfully to '{filepath}'.")
    except IOError as e:
        st.error(f"Failed to save test cases to '{filepath}': {e}")


# --- UI Components ---
def display_evaluation_ui(state, test_cases_file):
    """Displays the main UI for selecting and running evaluations."""
    st.header("Run Evaluation")

    if not state.test_cases:
        st.warning(
            "No test cases loaded. Please load or create test cases in the 'Test Case Management' section."
        )
        return

    test_case_options = [tc["name"] for tc in state.test_cases]
    selected_name = st.selectbox(
        "Select a Test Case to Evaluate",
        options=test_case_options,
        index=0,
        key="selected_test_case_dropdown",  # Added key for stability
    )

    # Find the selected test case dictionary
    selected_test_case = next(
        (tc for tc in state.test_cases if tc["name"] == selected_name), None
    )

    if not selected_test_case:
        st.error("Could not find the selected test case.")
        st.stop()

    # Display the details of the selected test case
    st.subheader("Test Case Details")
    st.markdown("**Input Query:**")
    st.info(selected_test_case["input"])

    run_button_disabled = not state.query_engine or not state.evaluator
    if st.button("Run Evaluation", disabled=run_button_disabled):
        if not state.query_engine or not state.evaluator:
            st.error("Please load the RAG and Evaluator first using the sidebar.")
            return

        # Prepare params for query engine from session state
        filter_metadata = {}
        if st.session_state.page_number:
            filter_metadata["page_number"] = st.session_state.page_number
        if st.session_state.title_filter:
            filter_metadata["title"] = st.session_state.title_filter

        experience_level_mapping = {"beginner": 0, "novice": 3, "advanced": 6}
        experience_years = experience_level_mapping.get(
            st.session_state.experience_level.lower(), 0
        )

        with st.spinner("Querying the RAG system..."):
            rag_result = state.query_engine.query(
                query=selected_test_case["input"],
                n_results=st.session_state.n_results,
                use_mmr=st.session_state.use_mmr,
                filter_metadata=filter_metadata if filter_metadata else None,
                experience_years=experience_years,
                llm_model=st.session_state.selected_llm,
            )
            actual_output = rag_result["answer"]

        st.subheader("Generated Output from RAG System")
        st.markdown(actual_output)

        with st.spinner("Running evaluation... This may take a moment."):
            llm_test_case = LLMTestCase(
                input=selected_test_case["input"],
                actual_output=actual_output,
                expected_output=selected_test_case.get("expected_output"),
            )
            evaluation_results = state.evaluator.evaluate(llm_test_case)

        # --- Save results to session state ---
        llm_name = st.session_state.selected_llm
        scores_dict = {name: score for name, score, reason in evaluation_results}

        # Find the index of the test case to update
        test_case_index = next(
            (
                i
                for i, tc in enumerate(state.test_cases)
                if tc["name"] == selected_test_case["name"]
            ),
            None,
        )

        if test_case_index is not None:
            # Prepare the result structure
            new_result_data = {
                "actual_output": actual_output,
                "scores": scores_dict,
                "last_evaluated": datetime.now().isoformat(),
            }
            # Update the specific LLM's results for that test case
            state.test_cases[test_case_index]["evaluation_results"][llm_name] = (
                new_result_data
            )
            st.success(
                f"Results for **{llm_name}** have been updated in the session. "
                "Go to the 'Test Case Management' tab to view and save changes."
            )

        st.subheader("Evaluation Results")
        total_score = 0
        valid_scores_count = 0
        for name, score, reason in evaluation_results:
            total_score += score if score is not None else 0.0
            if score is not None:
                valid_scores_count += 1
            st.markdown(f"#### {name}")
            st.metric(
                label="Score",
                value=f"{score:.2f}/1.0" if score is not None else "Failed",
            )
            with st.expander("Show Justification"):
                st.markdown(reason if reason else "No justification was provided.")

        if valid_scores_count > 0:
            avg_score = total_score / valid_scores_count
            st.success(f"**Average Score: {avg_score:.2f}/1.0**")
        else:
            st.error("Could not calculate an average score as all metrics failed.")

    if run_button_disabled:
        st.warning("RAG and Evaluator not loaded. Please use the sidebar to load them.")


def display_test_case_manager(state, test_cases_file):
    """Displays the UI for managing test cases in a master-detail view."""
    st.header("Test Case Management")

    with st.expander("Edit and Manage Test Cases", expanded=True):
        st.info(
            "Select a test case from the list to view its details. "
            "Editing, adding, and saving functionality will be re-enabled in the next steps."
        )

        # Master-detail layout
        col1, col2, col3 = st.columns([1, 1, 1])

        # --- Master List (Left Column) ---
        with col1:
            st.subheader("All Test Cases")
            if not state.test_cases:
                st.warning("No test cases loaded.")
            else:
                # Create a selectable list of test cases
                test_case_names = [
                    tc.get("name", f"Test Case {i+1}")
                    for i, tc in enumerate(state.test_cases)
                ]
                st.radio(
                    label="Select a test case",
                    options=range(len(test_case_names)),
                    format_func=lambda i: test_case_names[i],
                    key="selected_test_case_index",
                    label_visibility="collapsed",
                )

        # --- Detail View (Right Column) ---
        with col2:
            st.subheader("Details")
            selected_index = state.get("selected_test_case_index")

            if selected_index is not None and selected_index < len(state.test_cases):
                # Make the detail view editable
                selected_case = state.test_cases[selected_index]

                new_name = st.text_input(
                    "Name",
                    value=selected_case.get("name", ""),
                    key=f"name_{selected_index}",
                )
                new_input = st.text_area(
                    "Input",
                    value=selected_case.get("input", ""),
                    key=f"input_{selected_index}",
                    height=100,
                )
                new_expected_output = st.text_area(
                    "Expected Output",
                    value=selected_case.get("expected_output", ""),
                    key=f"expected_{selected_index}",
                    height=200,
                )

                # Update state immediately on change
                state.test_cases[selected_index]["name"] = new_name
                state.test_cases[selected_index]["input"] = new_input
                state.test_cases[selected_index]["expected_output"] = (
                    new_expected_output
                )

                # Display previous evaluation results
                st.markdown("---")
                st.subheader("Previous Evaluation Results")

                eval_results = selected_case.get("evaluation_results", {})
                if not eval_results:
                    st.info(
                        "No evaluation results found. Run an evaluation to see them here."
                    )
                else:
                    llm_names = sorted(list(eval_results.keys()))
                    llm_tabs = st.tabs(llm_names)

                    for i, llm_name in enumerate(llm_names):
                        with llm_tabs[i]:
                            result_data = eval_results[llm_name]
                            last_eval = result_data.get("last_evaluated", "N/A")
                            st.caption(f"Last Evaluated: {last_eval}")

                            st.text_area(
                                label="Actual Output",
                                value=result_data.get("actual_output", ""),
                                height=150,
                                disabled=True,
                                key=f"actual_output_{selected_index}_{llm_name}",
                            )

                            scores = result_data.get("scores", {})
                            if not scores:
                                st.write("No scores were recorded.")
                            else:
                                score_items = list(scores.items())
                                num_cols = min(len(score_items), 3)
                                if num_cols > 0:
                                    score_cols = st.columns(num_cols)
                                    for j, (metric, value) in enumerate(score_items):
                                        with score_cols[j % num_cols]:
                                            st.metric(
                                                label=metric,
                                                value=(
                                                    f"{value:.2f}"
                                                    if isinstance(value, (int, float))
                                                    else str(value)
                                                ),
                                            )

            elif not state.test_cases:
                st.info("Add a new test case to get started.")
            else:
                st.info(
                    "Select a test case from the list on the left to see its details."
                )

        # Add/Delete/Save controls
        st.markdown("---")
        with col1:
            if st.button("➕ Add New Test Case"):
                # Logic to add a new, blank test case
                new_case = {
                    "name": f"New Test Case {len(state.test_cases) + 1}",
                    "input": "",
                    "expected_output": "",
                    "evaluation_results": {},
                }
                state.test_cases.append(new_case)
                # Select the new test case
                state.selected_test_case_index = len(state.test_cases) - 1
                st.rerun()

        with col2:
            if st.button("💾 Save All Changes"):
                # Basic validation before saving
                valid_cases = []
                is_valid = True
                for i, case in enumerate(state.test_cases):
                    if not case.get("name") or not case.get("input"):
                        st.error(
                            f"Row {i+1}: 'name' and 'input' fields cannot be empty."
                        )
                        is_valid = False
                    else:
                        valid_cases.append(case)

                if is_valid:
                    save_test_cases(test_cases_file, state.test_cases)
                    st.rerun()

        with col3:
            if st.button("❌ Delete Selected Test Case"):
                if state.selected_test_case_index is not None:
                    del state.test_cases[state.selected_test_case_index]
                    # Adjust index if it's now out of bounds
                    if state.selected_test_case_index >= len(state.test_cases):
                        state.selected_test_case_index = len(state.test_cases) - 1
                    st.rerun()


# --- Main Application UI ---
def main():
    """Main function to run the Streamlit application."""
    st.title("RAG System Evaluation Assistant")

    state = get_session_state()
    test_cases_file = "src/modules/evaluation/evaluation_test_cases.json"

    # --- Sidebar for Configuration ---
    with st.sidebar:
        st.header("Configuration")
        st.subheader("RAG Source")
        rag_path = st.text_input("RAG Storage Path", value="./rag_storage")

        # Add embedder selection
        embedder_options = ["clip", "huggingface", "qwen", "siglip"]
        current_embedder = state.get("embedder_impl", "clip")
        if current_embedder not in embedder_options:
            embedder_options.insert(0, current_embedder)

        embedder_impl = st.selectbox(
            "Select Embedder Implementation",
            options=embedder_options,
            index=embedder_options.index(current_embedder),
            help="Choose the same embedder used during data ingestion.",
            key="embedder_impl",
        )

        if st.button("Load RAG and Evaluator"):
            if not os.path.isdir(rag_path):
                st.error(f"Directory not found: '{rag_path}'.")
            else:
                try:
                    with st.spinner("Loading Query Engine and Evaluator..."):
                        state.query_engine = QueryEngine(
                            persist_directory=rag_path,
                            embedder_impl=st.session_state.embedder_impl,
                        )
                        state.evaluator = Evaluator()
                    st.success("RAG and Evaluator loaded successfully!")
                except Exception as e:
                    st.error(f"Failed to load: {e}")

        st.markdown("---")
        st.subheader("Query Parameters")

        # Number of results to retrieve
        st.slider(
            "Number of results to retrieve",
            min_value=1,
            max_value=10,
            value=5,
            key="n_results",
        )

        # MMR toggle
        st.checkbox(
            "Use MMR for diversity",
            value=True,
            help="Enable Maximal Marginal Relevance to get more diverse search results.",
            key="use_mmr",
        )

        # Filter options
        st.subheader("Filters")
        st.number_input("Page Number", min_value=1, value=None, key="page_number")
        st.text_input("Title Filter", key="title_filter")

        # Experience level selector
        st.subheader("Response Personalization")
        st.selectbox(
            "Select Your Experience Level",
            options=["beginner", "novice", "advanced"],
            index=0,
            help="Tailor the response based on your experience",
            key="experience_level",
        )

        # --- LLM Model Selection ---
        st.subheader("LLM Model")
        llm_options = [
            "meta-llama/llama-4-maverick",
            "anthropic/claude-3.7-sonnet",
        ]
        selected_llm = st.selectbox(
            "Choose LLM",
            options=llm_options,
            index=llm_options.index(
                st.session_state.get("selected_llm", "meta-llama/llama-4-maverick")
            ),
            help="Choose which LLM model to use for answering questions.",
            key="selected_llm",
        )

        st.markdown("---")
        st.header("About")
        st.info(
            "This application is used to evaluate the performance of the RAG system."
        )

    # --- Load data on first run ---
    if not state.test_cases:
        state.test_cases = load_test_cases(test_cases_file)

    # --- Main Panel with Tabs ---
    tab1, tab2 = st.tabs(["Evaluation", "Test Case Management"])

    with tab1:
        display_evaluation_ui(state, test_cases_file)

    with tab2:
        display_test_case_manager(state, test_cases_file)


if __name__ == "__main__":
    main()
