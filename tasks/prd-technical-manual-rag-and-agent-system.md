# PRD: RAG System for Technical Manuals

## 1. Overview

This document outlines the requirements for building an advanced Retrieval-Augmented Generation (RAG) system designed to assist engineers and technicians with technical PDF manuals. The system will provide a chat-based interface for users to query information from documents.

The project will be developed in two main stages:
1.  **Core RAG Pipeline:** A robust system for processing, storing, and querying technical manuals with a focus on high-quality, context-aware responses tailored to user expertise.
2.  **Agentic Capabilities:** Integration of intelligent agents to extend the system's capabilities beyond the loaded documents, enabling web searches and queries against an internal inventory system.

This PRD is informed by existing artifacts, including `docs/architecture/001-PRD.md`, `docs/architecture/001-ADR.md`, and the progress documented in `docs/progress/20250601_1054_experimental_components_progress.md`.

## 2. Goals

### Stage 1: Core RAG Pipeline
*   To create a reliable pipeline for ingesting complex, image-heavy technical PDF manuals.
*   To implement a multi-modal RAG system that understands the relationship between text and images within the manuals.
*   To deliver a chat interface (based on the existing Streamlit app) that allows users to query the system using natural language.
*   To tailor responses based on the user's self-identified technical proficiency (e.g., beginner, expert).
*   To provide accurate, context-rich answers with clear references to the source material, including text and images.

### Stage 2: Agentic Capabilities
*   To enhance the system with an agent that can perform web searches for information not available in the manuals (e.g., updated part numbers, general troubleshooting).
*   To integrate a second agent capable of querying an internal inventory system for part availability, pricing, and location.
*   To implement a routing mechanism that intelligently directs user queries to the appropriate tool (RAG pipeline, web search, or inventory system).

## 3. User Personas & Stories

*   **Persona 1: Junior Technician (Beginner)**
    *   **Proficiency:** Limited experience, needs detailed, step-by-step guidance.
    *   **Story:** "As a junior technician, I want to ask the system 'How do I replace the primary air filter?' and receive a simple, step-by-step guide with diagrams from the manual so that I can complete the task correctly."

*   **Persona 2: Senior Engineer (Expert)**
    *   **Proficiency:** Deep technical knowledge, needs quick access to specific data or schematics.
    *   **Story:** "As a senior engineer, I want to ask 'What is the torque specification for the cylinder head bolts?' and get a concise answer with the exact values and the source page number, without needing the basic procedural steps."

*   **Persona 3: Technician with Agent Access**
    *   **Story (Web Search):** "As a technician, after finding a part number in the manual, I want to ask 'Are there any service bulletins for part #XYZ-123?' so that the system searches the web for the latest updates from the manufacturer."
    *   **Story (Inventory):** "As a technician, I want to ask 'How many units of part #XYZ-123 are in stock at the main warehouse?' so the system can query the inventory and I can plan my repair schedule."

## 4. Functional Requirements

### Stage 1: Core RAG Pipeline

1.  **PDF Processing (Ingestion):**
    *   The system must extract text, images, and structural elements (headers, lists, tables) from PDF documents using the Marker library.
    *   It must generate meaningful captions for all extracted images using the Florence-2 model.
    *   It must create semantically meaningful text chunks that preserve the relationship between text and associated images.
2.  **Vector Storage:**
    *   The system must use ChromaDB to store vector embeddings of the processed text and image captions.
    *   Embeddings will be generated using a multi-modal model (e.g., CLIP).
    *   Each vector must store rich metadata, including document title, page number, section hierarchy, and paths to related images.
3.  **Query Answering:**
    *   The system must provide a Streamlit-based chat interface (`rag_chat_app.py`).
    *   Users must be able to select their experience level (e.g., "Beginner", "Expert").
    *   The LLM's response generation must be tailored based on the selected experience level (e.g., providing more background for beginners).
    *   The system must retrieve relevant text chunks and images to generate an answer.
    *   The final answer must be displayed to the user, along with expandable source snippets and images.

### Stage 2: Agentic Capabilities

4.  **Agent Integration Framework:**
    *   The system must use LangChain as the framework for building and managing agents.
    *   An agent router/dispatcher must be created to analyze the user's query and decide which tool to use (RAG, Web Search, Inventory).
5.  **Web Search Agent:**
    *   A dedicated agent must be created that can use a search engine API (e.g., Tavily, Google Search) to answer queries.
    *   This agent should be triggered for queries that are unlikely to be answered by the technical manuals.
6.  **Inventory System Agent:**
    *   A dedicated agent must be created to interface with the inventory management system.
    *   This agent will require a stable, well-defined API (REST, GraphQL, etc.) to query for part information.

## 5. Non-Goals (Out of Scope)

*   PDF editing or creation capabilities.
*   Support for document formats other than PDF in the initial version.
*   User authentication or access control (for now).
*   Real-time processing of newly uploaded documents (ingestion is an offline batch process).

## 6. Design & Technical Considerations

*   **UI:** The existing Streamlit application (`src/modules/query_answering/rag_chat_app.py`) will serve as the foundation for the user interface.
*   **Modularity:** The system architecture should remain modular, as outlined in `docs/architecture/001-ADR.md`, to facilitate independent development and testing of the RAG pipeline and the agents.
*   **Configuration:** Key parameters (e.g., model names, database paths, API keys) should be managed via environment variables or a configuration file.
*   **Dependencies:** The project will leverage `langchain` for agentic components.

## 7. Success Metrics

*   **Retrieval Relevance:** High similarity scores between user queries and retrieved document chunks.
*   **Answer Quality:** User satisfaction with the accuracy and completeness of answers (can be measured via a simple "thumbs up/down" feedback mechanism in the UI).
*   **Response Time:** End-to-end latency from query submission to answer display remains within an acceptable range (e.g., <10 seconds for RAG queries).
*   **Agent Accuracy:** The agent router correctly dispatches queries to the appropriate tool in >90% of test cases.

## 8. Open Questions

1.  What is the specific web search tool/API we should use? (e.g., Tavily, Google Search, Bing Search)?
2.  What is the contract/specification for the Inventory System API? (e.g., endpoint, authentication, request/response format). This is a dependency for the inventory agent.
3.  How should the system behave if an agent (web search, inventory) fails to get a response? What is the fallback mechanism?