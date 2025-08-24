import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

from deepeval.test_case import LLMTestCase

# Compatibility for anext() in Python < 3.10
try:
    from builtins import anext
except ImportError:

    async def anext(async_iterator):
        return await async_iterator.__anext__()


import requests

# Set environment variables before other imports
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage

from src.modules.agent.simple_controller import SimpleAgentController
from src.modules.evaluation.evaluator import Evaluator
from src.modules.query.engine import QueryEngine
from src.modules.query_answering.rag_with_chroma import MultimodalChromaRAGQueryEngine

# --- Constants ---
AVATARS = {"user": "🧑‍💻", "assistant": "🤖"}

AGENT_ICONS = {
    "Supervisor": "🧠",
    "Manual Checker": "🔎",
    "Action Extractor": "🎬",
    "Web Searcher": "🔎",
    "Query Classifier": "🗂️",
    "Query Refiner": "✍️",
    "RAG": "📚",
    "Unnamed Agent": "🤖",
}

AGENT_COLORS = {
    "supervisor": "#FFA500",  # Orange
    "query_analyzer": "#00FFFF",  # Cyan
    "rag": "#90EE90",  # LightGreen
    "mcp": "#DDA0DD",  # Plum
    "search": "#ADD8E6",  # LightBlue
}

# --- App Configuration ---
# Defines the available RAG storages for the Multi-Agent mode.
# The keys are user-facing names, and the values are the parameters
# needed to initialize the RAG engine and agent controller.
RAG_CONFIGS = {
    "Qwen-based RAG": {
        "path": "./rag_storage/qwen_bm25_docu_summary_rewrite",
        "embedder": "qwen",
    },
    "CLIP-based RAG": {
        "path": "./rag_storage/clip_bm25_docu_summary_rewrite",
        "embedder": "clip",
    },
}

# Defines the available experience levels for consistent UI.
# The keys are user-facing names. The values contain the corresponding
# parameters for the simple RAG engine (years) and the agent controller (level).
EXPERIENCE_LEVELS = {
    "Beginner": {"years": 0, "agent_level": "NOVICE"},
    "Novice": {"years": 3, "agent_level": "EXPERIENCED"},
    "Advanced": {"years": 6, "agent_level": "EXPERT"},
}

# Load environment variables, overriding any existing ones
load_dotenv(override=True)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = "Simple RAG"
if "simple_rag_selection" not in st.session_state:
    st.session_state.simple_rag_selection = list(RAG_CONFIGS.keys())[0]
if "multiagent_rag_selection" not in st.session_state:
    st.session_state.multiagent_rag_selection = list(RAG_CONFIGS.keys())[0]
# Initialize keys for experience level selectors to prevent unbound errors
if "multiagent_experience_level_key" not in st.session_state:
    st.session_state.multiagent_experience_level_key = list(EXPERIENCE_LEVELS.keys())[
        1
    ]  # Default: Novice
if "simple_rag_experience_level_key" not in st.session_state:
    st.session_state.simple_rag_experience_level_key = list(EXPERIENCE_LEVELS.keys())[
        1
    ]  # Default: Novice
if "agent_steps" not in st.session_state:
    st.session_state.agent_steps = []

# --- New keys for simplified agent workflow ---
if "simple_agent_controller" not in st.session_state:
    st.session_state.simple_agent_controller = None
if "simple_agent_config" not in st.session_state:
    st.session_state.simple_agent_config = None
# --- New keys for interactive agent workflow ---
if "agent_generator" not in st.session_state:
    st.session_state.agent_generator = None
if "waiting_for_clarification" not in st.session_state:
    st.session_state.waiting_for_clarification = False
if "clarification_data" not in st.session_state:
    st.session_state.clarification_data = {}

# --- New keys for Evaluation Mode ---
if "eval_test_cases" not in st.session_state:
    st.session_state.eval_test_cases = []
if "eval_selected_test_case_name" not in st.session_state:
    st.session_state.eval_selected_test_case_name = None
if "eval_query_engine" not in st.session_state:
    st.session_state.eval_query_engine = None
if "eval_evaluator" not in st.session_state:
    st.session_state.eval_evaluator = None
if "eval_selected_test_case_index" not in st.session_state:
    st.session_state.eval_selected_test_case_index = (
        0 if st.session_state.get("eval_test_cases") else None
    )


# --- Data Loading & Saving for Evaluation ---
def eval_load_test_cases(filepath: str) -> list[dict]:
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


def eval_save_test_cases(filepath: str, test_cases: list[dict]):
    """Save test cases to a JSON file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(test_cases, f, indent=4)
        st.success(f"Test cases saved successfully to '{filepath}'.")
    except IOError as e:
        st.error(f"Failed to save test cases to '{filepath}': {e}")


def _eval_process_and_display_results(
    state,
    selected_test_case,
    actual_output,
    retrieved_contexts,
    evaluation_results,
):
    """Helper function to process, save, and display evaluation results."""
    llm_name = state.eval_selected_llm

    # Separate DeepEval and RAGAS results
    deepeval_results = {
        k: v
        for k, v in evaluation_results.items()
        if k in Evaluator()._define_criteria()
    }
    ragas_results = {
        k: v for k, v in evaluation_results.items() if k not in deepeval_results
    }

    # --- Score Calculation ---
    deepeval_scores = [
        r.get("score")
        for r in deepeval_results.values()
        if r and r.get("score") is not None
    ]
    ragas_scores = [
        r.get("score")
        for r in ragas_results.values()
        if r and r.get("score") is not None
    ]

    avg_deepeval_score = (
        sum(deepeval_scores) / len(deepeval_scores) if deepeval_scores else 0
    )
    avg_ragas_score = sum(ragas_scores) / len(ragas_scores) if ragas_scores else 0

    # The overall score is now just the DeepEval score
    average_score = avg_deepeval_score

    # --- Save Results ---
    # Combine all results for saving to JSON
    combined_scores_for_saving = {
        name: result.get("score")
        for name, result in evaluation_results.items()
        if result and result.get("score") is not None
    }

    # Find the test case to update
    test_case_index = next(
        (
            i
            for i, tc in enumerate(state.eval_test_cases)
            if tc["name"] == selected_test_case["name"]
        ),
        None,
    )

    if test_case_index is not None:
        new_result_data = {
            "actual_output": actual_output,
            "retrieved_contexts": retrieved_contexts,
            "scores": combined_scores_for_saving,
            "average_score": average_score,
            "last_evaluated": datetime.now().isoformat(),
        }
        # Use setdefault to create nested dictionaries if they don't exist
        rag_storage_name = state.eval_rag_selection
        search_strategy_name = state.get(
            "eval_search_strategy", "Vector + BM25 (Interleaving)"
        )

        eval_results = state.eval_test_cases[test_case_index]["evaluation_results"]
        rag_results = eval_results.setdefault(rag_storage_name, {})
        strategy_results = rag_results.setdefault(search_strategy_name, {})
        strategy_results[llm_name] = new_result_data

        st.success(
            f"Results for **{llm_name}** under **{rag_storage_name}** with strategy **{search_strategy_name}** have been updated."
        )

    st.markdown("---")
    st.subheader("Evaluation Results")

    # --- Display Scores ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Avg. DeepEval Score (0-1.0)",
            f"{avg_deepeval_score:.2f}",
            help="Average of detailed criteria scores.",
        )
    with col2:
        st.metric(
            "Avg. RAGAS Score (0-1.0)",
            f"{avg_ragas_score:.2f}",
            help="Average of RAGAS context and faithfulness scores.",
        )

    st.markdown("---")

    st.markdown("**Expected Answer (Ground Truth):**")
    expected_output = selected_test_case.get("expected_output")
    if expected_output:
        st.info(expected_output)
    else:
        st.info("No expected output was provided for this test case.")

    # --- Display Detailed Scores in Expanders ---
    with st.expander("Show Detailed Scores & Reasoning"):
        st.subheader("DeepEval Criteria")
        if not deepeval_results:
            st.warning("No DeepEval results to display.")
        else:
            for name, result in deepeval_results.items():
                score = result.get("score")
                reason = result.get("reason", "No reason provided.")
                if score is not None:
                    st.markdown(f"**{name}:** `{score:.2f}/1.0`")
                    st.caption(f"Reasoning: {reason}")
                else:
                    st.markdown(f"**{name}:** `Score not available`")
                    st.caption(f"Reasoning: {reason}")

        st.subheader("RAGAS Metrics")
        if not ragas_results:
            st.warning("No RAGAS results to display.")
        else:
            for name, result in ragas_results.items():
                score = result.get("score")
                if score is not None:
                    st.markdown(f"**{name}:** `{score:.2f}/1.0`")
                else:
                    st.markdown(f"**{name}:** `Score not available`")

    with st.expander("Show Retrieved Contexts"):
        if not retrieved_contexts:
            st.info("No retrieved contexts found.")
        else:
            for context in retrieved_contexts:
                st.markdown(f"- {context}")


def eval_display_evaluation_ui(state, test_cases_file):
    """Displays the main UI for selecting and running evaluations."""
    st.header("Run Evaluation")

    if not state.eval_test_cases:
        st.warning(
            "No test cases loaded. Please load or create test cases in the 'Test Case Management' section."
        )
        return

    test_case_options = [tc["name"] for tc in state.eval_test_cases]
    selected_name = st.selectbox(
        "Select a Test Case to Evaluate",
        options=test_case_options,
        index=0,
        key="eval_selected_test_case_dropdown",
    )

    selected_test_case = next(
        (tc for tc in state.eval_test_cases if tc["name"] == selected_name), None
    )

    if not selected_test_case:
        st.error("Could not find the selected test case.")
        st.stop()

    st.subheader("Test Case Details")
    st.markdown("**Input Query:**")
    st.info(selected_test_case["input"])

    run_button_disabled = not state.eval_query_engine or not state.eval_evaluator

    # --- Logic for enabling the re-run button ---
    rag_storage_name = state.eval_rag_selection
    search_strategy_name = state.get(
        "eval_search_strategy", "Vector + BM25 (Interleaving)"
    )
    llm_name = state.eval_selected_llm
    previous_results = (
        selected_test_case.get("evaluation_results", {})
        .get(rag_storage_name, {})
        .get(search_strategy_name, {})
        .get(llm_name, {})
    )
    can_rerun = (
        "actual_output" in previous_results and "retrieved_contexts" in previous_results
    )
    rerun_button_disabled = run_button_disabled or not can_rerun

    col1, col2 = st.columns(2)
    with col1:
        run_eval_pressed = st.button(
            "Ask RAG for New Output and Run Evaluation",
            disabled=run_button_disabled,
            key="eval_run_button",
            use_container_width=True,
        )
    with col2:
        rerun_eval_pressed = st.button(
            "Run Eval on Last Known Output",
            disabled=rerun_button_disabled,
            key="eval_rerun_button",
            use_container_width=True,
        )

    if run_eval_pressed:
        if not state.eval_query_engine or not state.eval_evaluator:
            st.error("Please load the RAG and Evaluator first using the sidebar.")
            return

        experience_years = EXPERIENCE_LEVELS[state.eval_experience_level]["years"]

        search_strategy = state.get(
            "eval_search_strategy", "Vector + BM25 (Interleaving)"
        )
        use_mmr = search_strategy == "Vector + MMR"
        fusion_method = (
            "interleave"
            if search_strategy == "Vector + BM25 (Interleaving)"
            else "rrf"
            if search_strategy == "Vector + BM25 (RRF)"
            else None
        )

        with st.spinner("Querying the RAG system..."):
            rag_result = state.eval_query_engine.query(
                query=selected_test_case["input"],
                n_results=state.eval_n_results,
                use_mmr=use_mmr,
                filter_metadata=None,
                experience_years=experience_years,
                llm_model=state.eval_selected_llm,
                fusion_method=fusion_method,
            )
            actual_output = rag_result["answer"]
            retrieved_contexts = [
                source.get("content", "") for source in rag_result.get("sources", [])
            ]

        st.subheader("Generated Output from RAG System")
        st.markdown(actual_output)

        with st.spinner("Running evaluation... This may take a moment."):
            llm_test_case = LLMTestCase(
                input=selected_test_case["input"],
                actual_output=actual_output,
                expected_output=selected_test_case.get("expected_output"),
            )
            evaluation_results = state.eval_evaluator.run_full_evaluation(
                test_case=llm_test_case, contexts=retrieved_contexts
            )

        _eval_process_and_display_results(
            state,
            selected_test_case,
            actual_output,
            retrieved_contexts,
            evaluation_results,
        )

    if rerun_eval_pressed:
        actual_output = previous_results["actual_output"]
        retrieved_contexts = previous_results["retrieved_contexts"]

        st.subheader("Last Known Output (Re-evaluating)")
        st.markdown(actual_output)

        with st.spinner("Re-running evaluation on previous output..."):
            llm_test_case = LLMTestCase(
                input=selected_test_case["input"],
                actual_output=actual_output,
                expected_output=selected_test_case.get("expected_output"),
            )
            evaluation_results = state.eval_evaluator.run_full_evaluation(
                test_case=llm_test_case,
                contexts=retrieved_contexts,
            )

        _eval_process_and_display_results(
            state,
            selected_test_case,
            actual_output,
            retrieved_contexts,
            evaluation_results,
        )

    if run_button_disabled:
        st.warning("RAG and Evaluator not loaded. Please use the sidebar to load them.")


def eval_display_test_case_manager(state, test_cases_file):
    """Displays the UI for managing test cases in a master-detail view."""
    st.header("Test Case Management")

    with st.expander("Edit and Manage Test Cases", expanded=True):
        st.info("Select a test case from the list to view its details.")

        # --- Master View and Controls (Top Section) ---
        master_col1, master_col2 = st.columns([3, 1])

        with master_col1:
            st.subheader("All Test Cases")
            if not state.eval_test_cases:
                st.warning("No test cases loaded.")
            else:
                test_case_names = [
                    tc.get("name", f"Test Case {i+1}")
                    for i, tc in enumerate(state.eval_test_cases)
                ]
                st.radio(
                    label="Select a test case",
                    options=range(len(test_case_names)),
                    format_func=lambda i: test_case_names[i],
                    key="eval_selected_test_case_index",
                    label_visibility="collapsed",
                )

        with master_col2:
            st.subheader("Actions")
            if st.button(
                "➕ Add New Test Case", key="eval_add_case", use_container_width=True
            ):
                new_case = {
                    "name": f"New Test Case {len(state.eval_test_cases) + 1}",
                    "input": "",
                    "expected_output": "",
                    "evaluation_results": {},
                }
                state.eval_test_cases.append(new_case)
                state.eval_selected_test_case_index = len(state.eval_test_cases) - 1
                st.rerun()

            if st.button(
                "💾 Save All Changes", key="eval_save_changes", use_container_width=True
            ):
                valid_cases = []
                is_valid = True
                for i, case in enumerate(state.eval_test_cases):
                    if not case.get("name") or not case.get("input"):
                        st.error(
                            f"Row {i+1}: 'name' and 'input' fields cannot be empty."
                        )
                        is_valid = False
                    else:
                        valid_cases.append(case)

                if is_valid:
                    eval_save_test_cases(test_cases_file, state.eval_test_cases)
                    st.rerun()

            if st.button(
                "❌ Delete Selected Test Case",
                key="eval_delete_case",
                use_container_width=True,
            ):
                if (
                    state.eval_selected_test_case_index is not None
                    and state.eval_test_cases
                ):
                    del state.eval_test_cases[state.eval_selected_test_case_index]
                    if state.eval_selected_test_case_index >= len(
                        state.eval_test_cases
                    ):
                        state.eval_selected_test_case_index = (
                            len(state.eval_test_cases) - 1
                        )
                    st.rerun()

        st.markdown("---")

        # --- Detail View (Bottom Section) ---
        st.subheader("Details")
        selected_index = state.get("eval_selected_test_case_index")

        if selected_index is not None and selected_index < len(state.eval_test_cases):
            selected_case = state.eval_test_cases[selected_index]

            new_name = st.text_input(
                "Name",
                value=selected_case.get("name", ""),
                key=f"eval_name_{selected_index}",
            )
            new_input = st.text_area(
                "Input",
                value=selected_case.get("input", ""),
                key=f"eval_input_{selected_index}",
                height=100,
            )
            new_expected_output = st.text_area(
                "Expected Output",
                value=selected_case.get("expected_output", ""),
                key=f"eval_expected_{selected_index}",
                height=200,
            )

            state.eval_test_cases[selected_index]["name"] = new_name
            state.eval_test_cases[selected_index]["input"] = new_input
            state.eval_test_cases[selected_index]["expected_output"] = (
                new_expected_output
            )

            st.markdown("---")
            st.subheader("Previous Evaluation Results")

            eval_results = selected_case.get("evaluation_results", {})
            if not eval_results:
                st.info(
                    "No evaluation results found. Run an evaluation to see them here."
                )
            else:
                # Level 1: RAG Storage
                rag_options = sorted(list(eval_results.keys()))
                if rag_options:
                    selected_rag = st.selectbox(
                        "RAG Storage",
                        options=rag_options,
                        key=f"eval_rag_select_{selected_index}",
                    )
                    rag_results = eval_results.get(selected_rag, {})

                    # Level 2: Search Strategy
                    strategy_options = sorted(list(rag_results.keys()))
                    if strategy_options:
                        selected_strategy = st.selectbox(
                            "Search Strategy",
                            options=strategy_options,
                            key=f"eval_strategy_select_{selected_index}",
                        )
                        strategy_results = rag_results.get(selected_strategy, {})

                        # Level 3: LLM Model
                        llm_options = sorted(list(strategy_results.keys()))
                        if llm_options:
                            selected_llm = st.selectbox(
                                "LLM Model",
                                options=llm_options,
                                key=f"eval_llm_select_{selected_index}",
                            )
                            result_data = strategy_results.get(selected_llm, {})

                            # --- Display selected result ---
                            last_eval = result_data.get("last_evaluated", "N/A")
                            st.caption(f"Last Evaluated: {last_eval}")

                            st.text_area(
                                label="Actual Output",
                                value=result_data.get("actual_output", ""),
                                height=150,
                                disabled=True,
                                key=f"eval_actual_output_{selected_index}_{selected_rag}_{selected_strategy}_{selected_llm}",
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
                        else:
                            st.info("No LLM results for this search strategy.")
                    else:
                        st.info("No search strategy results for this RAG storage.")
                else:
                    st.info("No RAG storage results for this test case.")

        elif not state.eval_test_cases:
            st.info("Add a new test case to get started.")
        else:
            st.info("Select a test case from the list on the left to see its details.")


def format_source(source: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Format a source document for display and extract its image paths."""
    chroma_metadata = source.get("metadata", {})
    content = source.get("content", "")

    # Format metadata text parts
    meta_parts = []
    if "title" in chroma_metadata:
        meta_parts.append(f"**Title:** {chroma_metadata['title']}")
    if "page_number" in chroma_metadata:
        meta_parts.append(f"**Page:** {chroma_metadata['page_number']}")
    if "section_level" in chroma_metadata:
        meta_parts.append(
            f"**Section Level:** {chroma_metadata.get('section_level', 'N/A')}"
        )
    elif chroma_metadata.get("additional_metadata"):
        try:
            additional_meta_dict = json.loads(chroma_metadata["additional_metadata"])
            if "section_level" in additional_meta_dict:
                meta_parts.append(
                    f"**Section Level:** {additional_meta_dict['section_level']}"
                )
        except (json.JSONDecodeError, TypeError):
            pass

    # Combine text parts
    text_display_parts = [
        f"**Score:** {source['score']:.3f}",
        *meta_parts,
        f"**Content:**\n{content[:500]}...",
    ]
    formatted_text_str = "\n\n".join(text_display_parts)

    # --- UNIVERSAL IMAGE EXTRACTION (HANDLES BOTH RAG FORMATS) ---
    # This logic is designed to be robust and find image paths regardless of
    # whether the RAG was built with the OLD or NEW pipeline.
    # It checks multiple possible locations for the image paths.
    actual_image_paths = []

    # 1. Primary location: `image_paths` key.
    #    - For NEW RAGs, this key is injected by the query engine.
    #    - For some OLD RAGs, this key might already exist.
    img_paths_direct = chroma_metadata.get("image_paths")
    if isinstance(img_paths_direct, list):
        actual_image_paths.extend(img_paths_direct)
    # Handle case where it's a JSON string (common in OLD RAG)
    elif isinstance(img_paths_direct, str):
        try:
            actual_image_paths.extend(json.loads(img_paths_direct))
        except (json.JSONDecodeError, TypeError):
            pass  # Ignore if it's not valid JSON

    # 2. Fallback location: Nested in `additional_metadata`.
    #    This is a pattern sometimes used by the OLD RAG pipeline.
    #    This check runs if the primary location yielded no images.
    if not actual_image_paths:
        additional_meta_json_str = chroma_metadata.get("additional_metadata")
        if additional_meta_json_str and isinstance(additional_meta_json_str, str):
            try:
                additional_meta_dict = json.loads(additional_meta_json_str)
                img_paths_from_additional = additional_meta_dict.get("image_paths")
                if isinstance(img_paths_from_additional, list):
                    actual_image_paths.extend(img_paths_from_additional)
            except json.JSONDecodeError:
                pass

    # Filter out non-string paths and ensure uniqueness (though should be unique from source)
    actual_image_paths = sorted(
        list(set(p for p in actual_image_paths if isinstance(p, str)))
    )

    return formatted_text_str, actual_image_paths


# --- Helper Functions ---
def clean_for_json(data: Any) -> Any:
    """Recursively clean data to make it JSON serializable."""
    if isinstance(data, dict):
        return {k: clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_json(item) for item in data]
    elif isinstance(data, BaseMessage):
        # Convert LangChain message to a serializable dict representation
        return {"type": data.type, "content": str(data.content)}
    else:
        # Return the item as is if it's serializable
        return data


def display_sources(sources: List[Dict[str, Any]], use_expander: bool = True):
    """
    Displays the sources of an answer, optionally within an expander.
    It uses format_source to correctly parse and display text and images.
    """

    def _render_source_content():
        if not sources:
            st.info("No sources found.")
            return

        for i, source_data_dict in enumerate(sources, 1):
            st.markdown(f"**Source {i}:**")

            # Use the robust format_source function to handle parsing
            formatted_source_text, image_paths_for_source = format_source(
                source_data_dict
            )

            st.markdown(formatted_source_text)

            if image_paths_for_source:
                st.markdown("**Related Images in this source chunk:**")
                # Display images in columns for this source
                cols = st.columns(min(3, len(image_paths_for_source)))
                for idx, img_path in enumerate(image_paths_for_source):
                    with cols[idx % 3]:
                        if os.path.exists(img_path):
                            try:
                                st.image(img_path, width=150)
                            except Exception:
                                st.error(f"Err loading {os.path.basename(img_path)}")
                        else:
                            st.caption(f"Not found: {os.path.basename(img_path)}")
            if i < len(sources):
                st.markdown("---")

    if use_expander:
        with st.expander("📚 View Sources"):
            _render_source_content()
    else:
        # Render directly for nested contexts, adding a separator for clarity
        st.markdown("---")
        st.markdown("**Sources from this step:**")
        _render_source_content()


def display_chat_message(
    role: str,
    content: str,
    sources: List[Dict[str, Any]] = None,
    agent_steps: List[Dict[str, Any]] = None,
):
    """Display a chat message with optional sources and agent steps."""
    with st.chat_message(role, avatar=AVATARS.get(role)):
        # Display agent workflow first if it exists
        if agent_steps:
            with st.expander("View Agent Workflow"):
                for step in agent_steps:
                    display_agent_step(step)

        # Display the main content of the message
        st.markdown(content)

        # Display sources if they exist
        if sources:
            display_sources(sources)


def display_agent_step(step: Dict[str, Any]):
    """Displays a single step of the agent workflow, showing inputs and outputs."""
    agent_name = step.get("agent", "Unnamed Agent")
    agent_output = step.get("output", {}).copy()  # Make a copy to avoid mutation

    icon = AGENT_ICONS.get(agent_name, "🤖")

    with st.container(border=True):
        st.markdown(f"**{icon} {agent_name.replace('_', ' ').title()}**")

        # Extract input summary, then remove it from output for clean display
        input_summary = agent_output.pop("_input_summary", None)

        if input_summary:
            st.markdown("###### Input")
            st.json(clean_for_json(input_summary))

        st.markdown("###### Output")

        # Special handling for supervisor's decision for clarity
        if agent_name == "supervisor" and "next_agent" in agent_output:
            next_agent = agent_output.pop("next_agent")
            reasoning = agent_output.pop("reasoning", "No reasoning provided.")
            final_query = agent_output.pop("final_query_for_rag", None)

            st.markdown(
                f"**Decision:** Route to `{next_agent.replace('_', ' ').title()}`"
            )
            st.caption(f"Reasoning: {reasoning}")

            if final_query:
                st.info(f"**Prepared Query for RAG Agent:**\n\n> {final_query}")

            # Display any remaining output in a popover
            other_output = {
                k: v for k, v in agent_output.items() if k not in ["current_agent"]
            }
            if other_output:
                with st.popover("View full output"):
                    st.json(clean_for_json(other_output))

        elif agent_output.get("messages"):
            # For other agents, display the primary message content directly
            st.markdown(agent_output["messages"][0].content)
            other_output = {k: v for k, v in agent_output.items() if k != "messages"}
            if other_output:
                with st.popover("View full output"):
                    st.json(clean_for_json(other_output))
        else:
            # Fallback for any other kind of output
            st.json(clean_for_json(agent_output))


def check_ollama_connection():
    """Check if the Ollama server is running and accessible."""
    try:
        # Use a short timeout to avoid long waits
        requests.get("http://localhost:11434", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False


def run_simple_rag_mode():
    """Defines the UI and logic for the Simple RAG mode."""

    # --- Sidebar Configuration for Simple RAG ---
    with st.sidebar:
        st.subheader("RAG Source")

        # Use the global RAG_CONFIGS to populate the selection
        st.selectbox(
            "Select RAG Storage",
            options=list(RAG_CONFIGS.keys()),
            key="simple_rag_selection",  # The selected value is stored here
            help="Choose the knowledge base to query.",
        )

        load_button_pressed = st.button("Load RAG")

        st.markdown("---")

        n_results = st.slider(
            "Number of results to retrieve", min_value=1, max_value=20, value=10
        )

        st.subheader("Search Strategy")
        search_strategy = st.radio(
            "Select Search Strategy",
            options=[
                "Vector Search Only",
                "Vector + MMR",
                "Vector + BM25 (Interleaving)",
                "Vector + BM25 (RRF)",
            ],
            index=2,
            help="Choose the search method.",
        )

        use_mmr = search_strategy == "Vector + MMR"
        fusion_method = (
            "interleave"
            if search_strategy == "Vector + BM25 (Interleaving)"
            else "rrf"
            if search_strategy == "Vector + BM25 (RRF)"
            else None
        )

        st.selectbox(
            "Select Your Experience Level",
            options=list(EXPERIENCE_LEVELS.keys()),
            index=1,  # Default to Novice
            key="simple_rag_experience_level_key",
            help="Tailor the response based on your experience",
        )
        experience_years = EXPERIENCE_LEVELS[
            st.session_state.simple_rag_experience_level_key
        ]["years"]

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
        )
        st.session_state["selected_llm"] = selected_llm

        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

    # --- Engine Initialization Logic ---
    if "query_engine" not in st.session_state or load_button_pressed:
        # Get the configuration for the selected RAG
        selected_rag_key = st.session_state.simple_rag_selection
        rag_config = RAG_CONFIGS[selected_rag_key]
        rag_path = rag_config["path"]
        rag_embedder = rag_config["embedder"]

        if not os.path.isdir(rag_path):
            st.error(f"Directory not found: '{rag_path}'.")
            st.stop()
        try:
            with st.spinner(f"Loading RAG from '{selected_rag_key}'..."):
                st.session_state.query_engine = MultimodalChromaRAGQueryEngine(
                    persist_directory=rag_path,
                    embedder_impl=rag_embedder,
                )
            # Clean up old session state keys if they exist
            if "rag_path" in st.session_state:
                del st.session_state["rag_path"]
            if "embedder_impl" in st.session_state:
                del st.session_state["embedder_impl"]

            st.session_state.messages = []
            st.toast("RAG loaded successfully! Chat has been cleared.", icon="✅")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to load RAG from '{selected_rag_key}'.")
            st.exception(e)
            if "query_engine" in st.session_state:
                del st.session_state.query_engine
            st.stop()

    # --- Main Chat UI for Simple RAG ---
    for message in st.session_state.messages:
        display_chat_message(
            message["role"],
            message["content"],
            message.get("sources"),
            message.get("agent_steps"),
        )

    if prompt := st.chat_input("Ask about the technical manual"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        display_chat_message("user", prompt)

        with st.spinner("Thinking..."):
            result = st.session_state.query_engine.query(
                query=prompt,
                n_results=n_results,
                experience_years=experience_years,
                fusion_method=fusion_method,
                use_mmr=use_mmr,
            )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "sources": result["sources"],
            }
        )
        display_chat_message("assistant", result["answer"], result["sources"])

        if result["relevant_images"]:
            st.subheader("Relevant Images (click to expand)")
            seen_images = set()
            for img_path in result["relevant_images"]:
                if img_path in seen_images:
                    continue
                seen_images.add(img_path)
                image_filename = os.path.basename(img_path)
                with st.expander(f"View Image: {image_filename}"):
                    if os.path.exists(img_path):
                        try:
                            st.image(img_path, use_container_width=True)
                        except Exception as e:
                            st.error(f"Could not load image {image_filename}: {e}")
                    else:
                        st.warning(f"Image file not found: {img_path}")

        # Handle inventory check results
        if result.get("status") == "inventory_check_complete":
            st.session_state.processing = False
            inventory_status = result.get("results", {}).get("inventory_status", {})
            tool_name = result.get("results", {}).get("tool_name", "Unknown Tool")

            st.write(f"#### Inventory Status for: **{tool_name.title()}**")
            status = inventory_status.get("status", "N/A")

            if status == "In Stock":
                st.success(f"**Status:** {inventory_status.get('status', 'N/A')}")
            else:
                st.error(f"**Status:** {inventory_status.get('status', 'N/A')}")

            st.info(f"**Quantity:** {inventory_status.get('quantity', 'N/A')}")
            st.info(f"**Location:** {inventory_status.get('location', 'N/A')}")

            if "note" in inventory_status:
                st.warning(f"**Note:** {inventory_status.get('note')}")

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"Here is the inventory status for {tool_name}.",
                }
            )


def run_multi_agent_mode():
    """Defines the UI and logic for the Multi-Agent mode using the new simplified workflow."""

    # --- Sidebar Configuration ---
    with st.sidebar:
        st.subheader("Agent Configuration")
        st.selectbox(
            "Select RAG Storage",
            options=list(RAG_CONFIGS.keys()),
            key="multiagent_rag_selection",
            help="Choose the knowledge base for the RAG agent.",
        )
        st.selectbox(
            "Select Your Experience Level",
            options=list(EXPERIENCE_LEVELS.keys()),
            index=1,
            key="experience_level_key",
            help="Tailor the agent's responses based on your expertise.",
        )
        st.markdown("---")
        st.subheader("Search Strategy")
        st.radio(
            "Select Search Strategy",
            options=[
                "Vector Search Only",
                "Vector + MMR",
                "Vector + BM25 (Interleaving)",
                "Vector + BM25 (RRF)",
            ],
            index=2,
            key="multiagent_search_strategy",
            help="Choose the search method for the RAG agent.",
        )

        st.subheader("LLM Model")
        llm_options = [
            "meta-llama/llama-4-maverick",
            "anthropic/claude-3.7-sonnet",
            "google/gemini-2.5-pro-preview",
        ]
        st.selectbox(
            "Choose LLM",
            options=llm_options,
            key="multiagent_selected_llm",
            help="Choose which LLM model to use for the agent.",
        )

        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

    # --- Agent Controller Initialization ---
    selected_rag_key = st.session_state.multiagent_rag_selection
    rag_config = RAG_CONFIGS[selected_rag_key]
    selected_llm = st.session_state.get(
        "multiagent_selected_llm", "meta-llama/llama-4-maverick"
    )

    # Unique key for the controller config to detect changes
    active_config = (selected_rag_key, selected_llm)
    if (
        "simple_agent_config" not in st.session_state
        or st.session_state.simple_agent_config != active_config
    ):
        with st.spinner("Initializing new agent system..."):
            st.session_state.simple_agent_controller = SimpleAgentController(
                rag_path=rag_config["path"],
                rag_embedder_impl=rag_config["embedder"],
                model_name=selected_llm,
            )
            st.session_state.simple_agent_config = active_config
            st.session_state.messages = []
            st.toast("New agent system initialized. Chat cleared.", icon="✅")
            st.rerun()

    # --- Chat UI ---
    for msg in st.session_state.messages:
        display_chat_message(
            msg["role"], msg["content"], msg.get("sources"), msg.get("agent_steps")
        )

    async def _run_agent_async():
        """
        Helper function to run the entire async agent generator to completion
        and update the UI with the final result.
        """
        # Initialize with any steps that were stored from a previous run (pre-clarification)
        all_steps = st.session_state.get("agent_steps", [])
        is_clarification_needed = False

        try:
            # Run the generator to completion, collecting all steps.
            async for step in st.session_state.agent_generator:
                all_steps.append(step)
                output = step.get("output", {})
                # Check for clarification requests mid-stream
                if output.get("status") == "clarification_needed":
                    st.session_state.waiting_for_clarification = True
                    st.session_state.clarification_data = {
                        "action": output.get("action"),
                        "options": output.get("options", []),
                    }
                    is_clarification_needed = True
                    break  # Stop processing if we need user input

            # Persist the steps so they can be displayed on the next run
            st.session_state.agent_steps = all_steps

            if is_clarification_needed:
                # Clean up generator and rerun to show the form
                st.session_state.agent_generator = None
                st.rerun()
                return

            # --- Process the FINAL result after the loop is done ---
            final_answer = "Could not determine a final answer."
            final_sources = []

            if all_steps:
                last_step = all_steps[-1]
                final_output = last_step.get("output", {})
                agent_name = last_step.get("agent")

                if agent_name == "Inventory Check":
                    tool_name = final_output.get("tool_name", "Unknown Tool")
                    status = final_output.get("inventory_status", {})
                    status_msg = status.get("status", "N/A")
                    quantity = status.get("quantity", "N/A")
                    location = status.get("location", "N/A")
                    note = status.get("note", "")
                    final_answer = (
                        f"**Inventory Status for: {tool_name.title()}**\n\n"
                        f"- **Status:** {status_msg}\n"
                        f"- **Quantity:** {quantity}\n"
                        f"- **Location:** {location}\n"
                    )
                    if note:
                        final_answer += f"- **Note:** {note}"

                elif agent_name == "Web Searcher":
                    summary = final_output.get("summary", "No summary provided.")
                    urls = final_output.get("urls", [])
                    url_markdown = "\n\n**Sources:**\n" + "\n".join(
                        f"- [{url}]({url})" for url in urls
                    )
                    final_answer = summary + url_markdown if urls else summary
                    final_sources = []
                else:
                    final_answer = final_output.get("answer", final_answer)
                    final_sources = final_output.get("sources", [])

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": final_answer,
                    "sources": final_sources,
                    "agent_steps": st.session_state.agent_steps,
                }
            )

            # Cleanup and rerun for a successful completion
            st.session_state.agent_generator = None
            st.session_state.agent_steps = []
            st.rerun()

        except Exception as e:
            error_message = f"An error occurred: {e}"
            st.error(error_message)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "agent_steps": all_steps,
                }
            )
            # Cleanup and rerun after an error
            st.session_state.agent_generator = None
            st.session_state.agent_steps = []
            st.rerun()

    # --- Agent Processing Loop ---
    if st.session_state.get("agent_generator"):
        # We need to run the async generator within Streamlit's event loop
        with st.spinner("Agent at work..."):
            asyncio.run(_run_agent_async())

    # --- Clarification Form ---
    if st.session_state.get("waiting_for_clarification"):
        # Display the agent steps that led to this clarification request
        if st.session_state.agent_steps:
            with st.chat_message("assistant", avatar=AVATARS["assistant"]):
                with st.expander("View Agent Workflow (leading to this question)"):
                    for step in st.session_state.agent_steps:
                        display_agent_step(step)

        with st.form(key="clarification_form"):
            st.markdown(
                "The agent requires more information. Please select the correct manual."
            )
            options = st.session_state.clarification_data.get("options", [])
            selected_manual = st.selectbox("Available Manuals:", options=options)
            submitted = st.form_submit_button("Submit Selection")

            if submitted:
                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": f"I selected the manual: {selected_manual}",
                    }
                )

                controller = st.session_state.simple_agent_controller
                action = st.session_state.clarification_data.get("action")

                # Get the latest RAG parameters from the UI
                search_strategy = st.session_state.multiagent_search_strategy
                use_mmr = search_strategy == "Vector + MMR"
                fusion_method = (
                    "interleave"
                    if search_strategy == "Vector + BM25 (Interleaving)"
                    else "rrf"
                    if search_strategy == "Vector + BM25 (RRF)"
                    else None
                )
                selected_level_key = st.session_state.experience_level_key
                experience_years = EXPERIENCE_LEVELS[selected_level_key]["years"]

                # Resume the workflow with the user's selection
                st.session_state.agent_generator = controller.resume_with_clarification(
                    action=action,
                    selected_manual=selected_manual,
                    experience_years=experience_years,
                    use_mmr=use_mmr,
                    fusion_method=fusion_method,
                    n_results=10,
                )

                # Reset clarification state and rerun to continue processing
                st.session_state.waiting_for_clarification = False
                st.session_state.clarification_data = {}
                st.rerun()

    # --- Chat Input ---
    if prompt := st.chat_input("Ask the new agent system..."):
        # Add user's message to history and reset agent steps
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.agent_steps = []

        controller = st.session_state.simple_agent_controller

        # Get the latest RAG parameters from the UI
        search_strategy = st.session_state.multiagent_search_strategy
        use_mmr = search_strategy == "Vector + MMR"
        fusion_method = (
            "interleave"
            if search_strategy == "Vector + BM25 (Interleaving)"
            else "rrf"
            if search_strategy == "Vector + BM25 (RRF)"
            else None
        )
        selected_level_key = st.session_state.experience_level_key
        experience_years = EXPERIENCE_LEVELS[selected_level_key]["years"]

        # Create the generator and store it in session state to be processed above
        st.session_state.agent_generator = controller.process_query(
            query=prompt,
            experience_years=experience_years,
            use_mmr=use_mmr,
            fusion_method=fusion_method,
        )
        st.rerun()


def run_evaluation_mode():
    """Defines the UI and logic for the new Evaluation mode."""
    st.title("RAG System Evaluation Assistant")

    test_cases_file = "src/modules/evaluation/evaluation_test_cases.json"

    # Load test cases if not already loaded, before any UI is rendered
    if not st.session_state.eval_test_cases:
        st.session_state.eval_test_cases = eval_load_test_cases(test_cases_file)

    # --- Sidebar for Configuration ---
    with st.sidebar:
        st.header("Evaluation Configuration")

        # Use RAG_CONFIGS from the main app for consistency
        st.selectbox(
            "Select RAG Storage",
            options=list(RAG_CONFIGS.keys()),
            key="eval_rag_selection",
            help="Choose the knowledge base to evaluate.",
        )

        if st.button("Load RAG and Evaluator", key="eval_load_button"):
            selected_rag_key = st.session_state.eval_rag_selection
            rag_config = RAG_CONFIGS[selected_rag_key]
            rag_path = rag_config["path"]
            rag_embedder = rag_config["embedder"]

            if not os.path.isdir(rag_path):
                st.error(f"Directory not found: '{rag_path}'.")
            else:
                try:
                    with st.spinner("Loading Query Engine and Evaluator..."):
                        # Use eval_ prefixed keys for state isolation
                        st.session_state.eval_query_engine = QueryEngine(
                            persist_directory=rag_path,
                            embedder_impl=rag_embedder,
                        )
                        st.session_state.eval_evaluator = Evaluator()
                    st.success("RAG and Evaluator loaded successfully!")
                except Exception as e:
                    st.error(f"Failed to load: {e}")

        st.markdown("---")
        st.subheader("Query Parameters")

        st.slider(
            "Number of results to retrieve",
            min_value=1,
            max_value=20,
            value=10,
            key="eval_n_results",
        )

        st.subheader("Search Strategy")
        st.radio(
            "Select Search Strategy",
            options=[
                "Vector Search Only",
                "Vector + MMR",
                "Vector + BM25 (Interleaving)",
                "Vector + BM25 (RRF)",
            ],
            index=2,
            key="eval_search_strategy",
            help="Choose the search method.",
        )

        st.subheader("Response Personalization")
        st.selectbox(
            "Select Your Experience Level",
            options=list(EXPERIENCE_LEVELS.keys()),
            index=1,
            help="Tailor the response based on your experience",
            key="eval_experience_level",
        )

        st.subheader("LLM Model")
        llm_options = [
            "meta-llama/llama-4-maverick",
            "anthropic/claude-3.7-sonnet"
        ]
        st.selectbox(
            "Choose LLM",
            options=llm_options,
            index=0,
            key="eval_selected_llm",
            help="Choose which LLM model to use for evaluation.",
        )

    # --- Main Panel with Tabs ---
    tab1, tab2 = st.tabs(["Evaluation", "Test Case Management"])

    with tab1:
        eval_display_evaluation_ui(st.session_state, test_cases_file)

    with tab2:
        eval_display_test_case_manager(st.session_state, test_cases_file)


def main():
    st.set_page_config(layout="wide")
    st.title("Technical Manual Chat Assistant")

    with st.sidebar:
        st.header("Configuration")
        st.subheader("Mode")

        def on_mode_change():
            # We don't clear messages anymore, to preserve chat history
            # when switching to and from evaluation mode.
            pass

        st.radio(
            "Choose operation mode:",
            ("Simple RAG", "Multi-Agent", "Evaluation"),
            key="mode",
            on_change=on_mode_change,
            label_visibility="collapsed",
        )
        st.markdown("---")

    # --- Mode Dispatcher ---
    if st.session_state.mode == "Simple RAG":
        run_simple_rag_mode()
    elif st.session_state.mode == "Multi-Agent":
        run_multi_agent_mode()
    elif st.session_state.mode == "Evaluation":
        run_evaluation_mode()
    else:
        st.error("Invalid mode selected.")


if __name__ == "__main__":
    main()
