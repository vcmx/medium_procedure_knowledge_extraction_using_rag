import os
import json
import logging
import warnings
from typing import Any, Dict, List, Tuple

# Comprehensive warning suppression for development
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

# Environment setup to prevent various compatibility issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Load environment variables, overriding any existing ones
load_dotenv(override=True)

# Import from the fixed version
from integrated_research_graph_v2 import (
    research_graph,
    set_rag_config,
    MultimodalChromaRAGQueryEngine,
    rag_query_tool,
    logger,
    is_rag_configured,
    get_rag_engine
)

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Research Assistant with RAG",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent_history" not in st.session_state:
    st.session_state.agent_history = []
if "rag_configured" not in st.session_state:
    st.session_state.rag_configured = False
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "multi_agent"


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


def display_chat_message(role: str, content: str, sources: List[Dict[str, Any]] = None):
    """Display a chat message with optional sources and their images."""
    with st.chat_message(role):
        st.markdown(content)

        if sources:
            with st.expander("View Sources"):
                for i, source_data_dict in enumerate(sources, 1):
                    st.markdown(f"**Source {i}:**")

                    # Get formatted text and image paths for this source
                    formatted_source_text, image_paths_for_source = format_source(source_data_dict)
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
                                        st.error(f"Error loading {os.path.basename(img_path)}")
                                else:
                                    st.caption(f"Not found: {os.path.basename(img_path)}")
                    if i < len(sources):
                        st.markdown("---")


def display_agent_step(step_data: Dict[str, Any], step_number: int):
    """Display an agent step in the multi-agent mode."""
    with st.expander(f"Step {step_number}: Agent Execution", expanded=False):
        for agent_name, agent_data in step_data.items():
            if "messages" in agent_data and agent_data["messages"]:
                for msg in agent_data["messages"]:
                    agent_display_name = getattr(msg, 'name', agent_name).capitalize()
                    st.markdown(f"**{agent_display_name} Agent:**")
                    st.markdown(msg.content)
                    st.markdown("---")


def main():
    st.title("🧠 Multi-Agent Research Assistant with RAG")
    st.markdown("Choose between multi-agent research or direct RAG chat modes")

    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Mode selection
        mode = st.radio(
            "Select Mode",
            ["Multi-Agent Research", "Direct RAG Chat"],
            key="mode_selector"
        )
        st.session_state.current_mode = "multi_agent" if mode == "Multi-Agent Research" else "rag_chat"
        
        st.markdown("---")

        # RAG Configuration
        st.subheader("RAG Configuration")
        
        rag_path = st.text_input(
            "RAG Storage Path",
            value=st.session_state.get("rag_path", "./florence_clip_chroma_relational"),
            help="Path to the directory containing RAG data"
        )
        
        embedder_options = ["clip", "huggingface", "qwen", "siglip"]
        current_embedder = st.session_state.get("embedder_impl", "clip")
        if current_embedder not in embedder_options:
            embedder_options.insert(0, current_embedder)
        
        embedder_selection = st.selectbox(
            "Embedder Model",
            options=embedder_options,
            index=embedder_options.index(current_embedder),
            help="The embedding model used to build the RAG"
        )
        
        # LLM Model Selection
        llm_options = [
            "meta-llama/llama-4-maverick",
            "anthropic/claude-3.7-sonnet", 
            "google/gemini-2.5-pro-preview",
        ]
        selected_llm = st.selectbox(
            "Choose LLM",
            options=llm_options,
            index=llm_options.index(st.session_state.get("selected_llm", "anthropic/claude-3.7-sonnet")),
            help="Choose which LLM model to use"
        )
        st.session_state["selected_llm"] = selected_llm
        
        # Configure RAG button
        if st.button("Configure RAG"):
            if not os.path.isdir(rag_path):
                st.error(f"Directory not found: '{rag_path}'. Please provide a valid path.")
            else:
                with st.spinner("Configuring RAG..."):
                    try:
                        success = set_rag_config(
                            persist_directory=rag_path,
                            embedder_impl=embedder_selection,
                            llm_model=selected_llm
                        )
                        if success:
                            st.session_state.rag_configured = True
                            st.session_state.rag_path = rag_path
                            st.session_state.embedder_impl = embedder_selection
                            st.success("✅ RAG configured successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to configure RAG. Check logs for details.")
                    except Exception as e:
                        st.error(f"❌ Error configuring RAG: {str(e)}")
                        logger.error(f"RAG configuration error: {e}", exc_info=True)
        
        st.markdown("---")
        
        # RAG-specific settings (only shown in RAG chat mode)
        if st.session_state.current_mode == "rag_chat":
            st.subheader("RAG Chat Settings")
            
            n_results = st.slider("Number of results", min_value=1, max_value=10, value=5)
            
            # Filter options
            page_number = st.number_input("Page Number Filter", min_value=1, value=None)
            title_filter = st.text_input("Title Filter")
            
            use_mmr = st.checkbox("Use MMR for diversity", value=True)
            
            experience_level = st.selectbox(
                "Experience Level",
                options=["beginner", "novice", "advanced"],
                index=0
            )
            experience_mapping = {"beginner": 0, "novice": 3, "advanced": 6}
            experience_years = experience_mapping.get(experience_level.lower(), 0)
        
        # Clear chat button
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.session_state.agent_history = []
            st.rerun()

    # Status indicator
    if is_rag_configured():
        st.success("✅ RAG is configured and ready")
    else:
        st.warning("⚠️ RAG not configured - configure in sidebar for full functionality")

    # Mode-specific content
    if st.session_state.current_mode == "multi_agent":
        st.subheader("🤖 Multi-Agent Research Mode")
        st.markdown("The agents will collaborate to answer your questions using web search, code execution, and RAG.")
        
        # Display agent history
        if st.session_state.agent_history:
            st.subheader("Agent Execution History")
            for i, step in enumerate(st.session_state.agent_history, 1):
                display_agent_step(step, i)
        
        # Display chat messages
        for message in st.session_state.messages:
            if message["role"] in ["user", "assistant"]:
                display_chat_message(message["role"], message["content"])
        
        # Chat input for multi-agent
        if prompt := st.chat_input("Ask the agents anything (they can search web, run code, or query RAG)"):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            display_chat_message("user", prompt)
            
            # Prepare state for multi-agent system
            state_input = {
                "messages": [HumanMessage(content=prompt)],
            }
            
            # Execute multi-agent workflow
            with st.spinner("Agents are collaborating..."):
                final_response = ""
                step_count = 0
                
                for step in research_graph.stream(state_input):
                    step_count += 1
                    st.session_state.agent_history.append(step)
                    
                    # Display the step with the correct step number
                    display_agent_step(step, step_count)
                    
                    # Extract the final response from the last agent
                    for agent_name, agent_data in step.items():
                        if "messages" in agent_data and agent_data["messages"]:
                            final_response = agent_data["messages"][-1].content
            
            # Add final response to chat
            if final_response:
                st.session_state.messages.append({"role": "assistant", "content": final_response})
                display_chat_message("assistant", final_response)
    
    else:  # rag_chat mode
        st.subheader("📚 Direct RAG Chat Mode")
        st.markdown("Chat directly with your documents and technical manuals.")
        
        # Check if RAG is configured
        if not is_rag_configured():
            st.warning("Please configure RAG in the sidebar before chatting.")
            return
        
        # Get RAG engine for direct chat
        rag_engine = get_rag_engine()
        if rag_engine is None:
            st.error("RAG engine not available. Please reconfigure RAG.")
            return
        
        # Display chat messages
        for message in st.session_state.messages:
            display_chat_message(
                message["role"], 
                message["content"], 
                message.get("sources")
            )
        
        # Chat input for RAG mode
        if prompt := st.chat_input("Ask about your technical documents"):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            display_chat_message("user", prompt)
            
            # Prepare metadata filters
            filter_metadata = {}
            if 'page_number' in locals() and page_number:
                filter_metadata["page_number"] = page_number
            if 'title_filter' in locals() and title_filter:
                filter_metadata["title"] = title_filter
            
            # Query RAG system
            with st.spinner("Searching documents..."):
                try:
                    result = rag_engine.query(
                        query=prompt,
                        n_results=n_results if 'n_results' in locals() else 5,
                        filter_metadata=filter_metadata if filter_metadata else None,
                        experience_years=experience_years if 'experience_years' in locals() else 0,
                        use_mmr=use_mmr if 'use_mmr' in locals() else True,
                    )
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result["sources"],
                    })
                    
                    # Display assistant response
                    display_chat_message("assistant", result["answer"], result["sources"])
                    
                    # Display relevant images if any
                    if result["relevant_images"]:
                        st.subheader("📷 Relevant Images")
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
                
                except Exception as e:
                    st.error(f"Error querying RAG system: {e}")

    # Footer information
    st.markdown("---")
    with st.expander("ℹ️ How to Use"):
        st.markdown("""
        ### Multi-Agent Research Mode
        - Agents collaborate to answer complex questions
        - **Search Agent**: Gets current information from the web
        - **Code Agent**: Executes Python code and creates visualizations  
        - **RAG Agent**: Searches your local documents and manuals
        - Example: "Search for recent AI developments and create a chart showing the trends"
        
        ### Direct RAG Chat Mode
        - Chat directly with your documents
        - More control over search parameters
        - View sources and related images
        - Example: "How do I remove the camshaft sprocket?"
        
        ### Setup Instructions
        1. Configure RAG in the sidebar with your document storage path
        2. Select the appropriate embedder model used for your RAG
        3. Choose your preferred LLM model
        4. Click "Configure RAG" to initialize the system
        5. Start chatting!
        """)


if __name__ == "__main__":
    main()