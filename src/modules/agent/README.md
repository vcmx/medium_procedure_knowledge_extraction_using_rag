# Agent System

Multi-agent system built with LangGraph for coordinating specialized agents in technical documentation assistance.

## Overview

This module implements a hierarchical agent architecture where a **Supervisor Agent** coordinates specialized sub-agents:

- **Query Analyzer Agent**: Wraps the existing query analyzer module for intent analysis and clarification
- **Search Agent**: Web search capabilities using Tavily API for real-time information
- **RAG Agent**: Placeholder for retrieval-augmented generation capabilities  
- **MCP Agent**: Placeholder for Model Context Protocol tool integration

## Architecture

### System Overview

```mermaid
flowchart TB
    %% User Input Layer
    A[User Query] --> B[Agent Controller]
    
    %% Controller and Session Management
    B --> C{Session Manager}
    C --> D[Create/Load Session]
    D --> E[Build Initial State]
    
    %% LangGraph Workflow
    E --> F[LangGraph StateGraph]
    
    %% Supervisor Decision Layer
    F --> G[Supervisor Agent]
    G --> H{Routing Decision}
    
    %% Agent Execution Layer
    H -->|Initial Query| I[Query Analyzer Agent]
    H -->|Need Info| J[RAG Agent]
    H -->|Need Tools| K[MCP Agent]
    H -->|Need Search| L[Search Agent]
    H -->|Complete| M[FINISH/END]
    
    %% Query Analyzer Flow
    subgraph I[" Query Analyzer Agent "]
        I1[Intent Analysis]
        I2[Entity Extraction]
        I3[Query Enhancement]
        I4[Step-back Questions]
        I5[Clarification Check]
        I1 --> I2 --> I3 --> I4 --> I5
    end
    
    %% RAG Agent Flow
    subgraph J[" RAG Agent "]
        J1[Document Retrieval]
        J2[Vector Search]
        J3[Result Ranking]
        J4[Response Generation]
        J1 --> J2 --> J3 --> J4
    end
    
    %% MCP Agent Flow
    subgraph K[" MCP Agent "]
        K1[Tool Selection]
        K2[Parameter Extraction]
        K3[Tool Execution]
        K4[Result Processing]
        K1 --> K2 --> K3 --> K4
    end
    
    %% Search Agent Flow
    subgraph L[" Search Agent "]
        L1[Tavily API Call]
        L2[Result Processing]
        L3[LLM Summarization]
        L4[Response Formatting]
        L1 --> L2 --> L3 --> L4
    end
    
    %% Return to Supervisor
    I --> G
    J --> G
    K --> G
    L --> G
    
    %% Output Processing
    M --> N[Stream Results]
    N --> O[Final Response]
    
    %% Styling
    classDef userInput fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef controller fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef supervisor fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef agent fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef workflow fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef output fill:#e0f2f1,stroke:#004d40,stroke-width:2px
    
    class A userInput
    class B,C,D,E controller
    class F workflow
    class G,H supervisor
    class I,J,K,L agent
    class M,N,O output
```

### Agent Interaction Flow

```mermaid
sequenceDiagram
    participant U as User
    participant AC as AgentController
    participant LG as LangGraph
    participant S as Supervisor
    participant QA as QueryAnalyzer
    participant RA as RAGAgent
    participant SA as SearchAgent
    participant MC as MCPAgent
    
    U->>AC: Submit Query
    AC->>AC: Create/Load Session
    AC->>LG: Initialize StateGraph
    
    loop Until FINISH
        LG->>S: Current State
        S->>S: Analyze Context
        S->>S: Make Routing Decision
        
        alt Query Analysis Needed
            S->>QA: Route to Query Analyzer
            QA->>QA: Analyze Intent
            QA->>QA: Extract Entities
            QA->>QA: Generate Step-back Questions
            
            alt Clarification Needed
                QA-->>U: Request Clarification
                U-->>QA: Provide Responses
            end
            
            QA->>S: Return Analysis Results
            
        else Information Retrieval Needed
            S->>RA: Route to RAG Agent
            RA->>RA: Search Documents
            RA->>RA: Rank Results
            RA->>RA: Generate Response
            RA->>S: Return Retrieval Results
            
        else Web Search Needed
            S->>SA: Route to Search Agent
            SA->>SA: Call Tavily API
            SA->>SA: Process Results
            SA->>SA: Summarize with LLM
            SA->>S: Return Search Results
            
        else Tool Execution Needed
            S->>MC: Route to MCP Agent
            MC->>MC: Select Tools
            MC->>MC: Execute Tools
            MC->>MC: Process Results
            MC->>S: Return Tool Results
            
        else Task Complete
            S->>LG: FINISH Signal
        end
    end
    
    LG->>AC: Stream Results
    AC->>U: Final Response
```

### Simple Agent Hierarchy

```mermaid
graph TD
    A[Supervisor Agent] --> B[Query Analyzer Agent]
    A --> C[Search Agent]
    A --> D[RAG Agent]
    A --> E[MCP Agent]
    
    A -.- F[Coordinates all agents]
    B -.- G[Intent analysis & clarification]
    C -.- H[Web search & real-time data]
    D -.- I[Retrieval & answer generation]
    E -.- J[Tool execution & calculations]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e3f2fd
    style D fill:#e8f5e8
    style E fill:#fff3e0
```

## Components

### AgentController
Main interface for the agent system:
- Session management
- Agent coordination via LangGraph
- Response formatting
- Error handling

### SupervisorAgent
Decision-making agent that routes queries to appropriate sub-agents based on:
- Current workflow stage
- Query analysis results
- Task complexity
- Available agent capabilities

### QueryAnalyzerAgent
Wrapper around the existing query analyzer module:
- Intent analysis and entity extraction
- Clarification workflow
- Query enhancement and synthesis
- Relevance checking
- Step-back question generation

### SearchAgent
Web search capabilities for real-time information:
- Tavily API integration for web search
- Current events and latest information retrieval
- Step-back question answering
- Search result summarization with LLM
- Configurable search depth and result limits

### RAGAgent (Placeholder)
Future integration with retrieval systems:
- Vector database search
- Multimodal content retrieval
- Answer generation
- Result ranking

### MCPAgent (Placeholder)
Future integration with external tools:
- Calculation and simulation tools
- API integrations
- Safety validation
- Real-time data access

## Usage

### Basic Usage

```python
from src.modules.agent import AgentController

# Initialize controller
controller = AgentController(
    llm_model="llama3.2",
    enable_rag=True,
    enable_mcp=True,
    enable_search=True  # Enable web search capabilities
)

# Create session
session_id = controller.create_session(user_level="EXPERIENCED")

# Process query
for step in controller.process_query("How do I change engine oil?", session_id):
    agent_name = step["agent"]
    output = step["output"]
    print(f"{agent_name}: {output}")
```

### Clarification Workflow

```python
# Process query that needs clarification
for step in controller.process_query("How do I change this?", session_id):
    if step["output"].get("clarification_needed"):
        questions = step["output"]["clarification_questions"]
        # Collect user responses...
        
        # Continue with responses
        responses = {"What is 'this'?": "engine oil"}
        for step in controller.process_query(
            query, session_id, clarification_responses=responses
        ):
            # Process clarified query...
```

### Web Search Integration

```python
# Initialize with search enabled
controller = AgentController(
    llm_model="llama3.2",
    enable_search=True,
    tavily_api_key="your-api-key"  # Optional: can use env var
)

# Process query that may use search
for step in controller.process_query("What are the latest AI developments?", session_id):
    agent_name = step["agent"]
    output = step["output"]
    
    if agent_name == "search":
        # Search results available
        search_results = output.get("analysis_results", {}).get("search_results", {})
        print(f"Found {search_results.get('num_results', 0)} search results")
```

### Step-Back Question Search

The system can automatically search for step-back questions generated during query analysis:

```python
# When query analyzer generates step-back questions,
# the interactive demo offers to search for them:
# "Would you like to search the web for these questions? (y/n)"

# Step-back questions might include:
# - "What is the history of AI?"
# - "How do neural networks work?"
# - "What are recent AI breakthroughs?"

# Each question is searched automatically and results
# provide additional context for better answers
```

### Session Management

```python
# List active sessions
sessions = controller.list_sessions()

# Get session info
info = controller.get_session_info(session_id)

# Clear session
controller.clear_session(session_id)

# Get agent status
status = controller.get_agent_status()
```

## State Management & Workflow

### Agent State Structure
The system uses a shared state that flows through all agents:

```python
AgentState = TypedDict("AgentState", {
    # Core messaging
    "messages": Annotated[List[HumanMessage | AIMessage], add_messages],
    
    # Agent tracking
    "current_agent": str,
    "next_agent": Optional[str],
    
    # Workflow control
    "workflow_stage": str,  # initial, analyzing, clarifying, analyzed, retrieved, complete
    "task_description": str,
    
    # Query analysis
    "clarification_needed": bool,
    "clarification_questions": List[str],
    "user_responses": Dict[str, str],
    "original_query": Optional[str],
    "enhanced_query": Optional[str],
    "analysis_results": Dict[str, Any],
    
    # Retrieval & execution
    "retrieval_results": Optional[Dict[str, Any]],
    "tool_calls": List[Dict[str, Any]],
    "tool_results": List[Any],
    
    # Session management
    "session_id": str,
    "user_level": str  # NOVICE, EXPERIENCED, EXPERT
})
```

### Workflow Stage Transitions

```mermaid
stateDiagram-v2
    [*] --> initial: New Query
    initial --> analyzing: Query Analyzer
    analyzing --> clarifying: Needs Clarification
    analyzing --> analyzed: Analysis Complete
    clarifying --> analyzing: Responses Provided
    analyzed --> retrieved: RAG/Search Agent
    analyzed --> processed: MCP Agent
    retrieved --> complete: Results Ready
    processed --> complete: Tools Executed
    complete --> [*]: Finish
    
    analyzing --> error: Analysis Failed
    retrieved --> error: Retrieval Failed
    processed --> error: Tool Failed
    error --> [*]: Error Handled
```

### Routing Logic
The Supervisor uses rule-based routing for efficiency:

1. **Initial Stage** → Query Analyzer
2. **Clarifying (no responses)** → Wait for user
3. **Clarifying (with responses)** → Query Analyzer
4. **Analyzed** → RAG/Search/MCP based on intent
5. **Retrieved/Processed/Searched** → FINISH
6. **Error** → FINISH with error message

### Workflow Stages

1. **initial**: New query received
2. **analyzing**: Query analysis in progress
3. **clarifying**: Waiting for/processing clarification
4. **analyzed**: Query understood, routing to next agent
5. **retrieved**: Information retrieval complete
6. **processed**: Tool execution complete
7. **searched**: Web search complete
8. **complete**: Task finished successfully
9. **error**: Error occurred, workflow terminated

## Testing

### Run Individual Component Tests

```bash
# Test supervisor agent routing
python tests/agent/test_supervisor_agent.py

# Test query analyzer agent integration  
python tests/agent/test_query_analyzer_agent.py

# Test agent controller coordination
python tests/agent/test_agent_controller.py
```

### Run Full Demo

```bash
# Install dependencies
pip install -r requirements-agent.txt

# Run automated demo (shows all features)
python tests/agent/demo_agent_system.py

# Run interactive demo (user-driven exploration)
python tests/agent/interactive_agent_demo.py

# Test search agent functionality
python tests/agent/test_search_agent.py

# Demo search integration with step-back questions
python tests/agent/demo_enhanced_search.py
```

### Interactive Demo Features

The interactive demo allows you to:
- Submit your own queries in real-time
- Handle clarification workflows interactively
- Use web search for current information (when enabled)
- Search step-back questions automatically
- Manage multiple sessions
- Switch between user expertise levels
- Explore different agent capabilities
- View system status and configuration

Commands available in interactive mode:
- `query <text>` - Submit a query
- `search <query>` - Direct web search (when search enabled)
- `session new/list/switch/clear` - Manage sessions
- `status` - View agent system status
- `demo` - Run example queries (includes search examples)
- `help` - Show available commands

### Test Categories

**Supervisor Agent Tests:**
- Routing decisions based on workflow stage
- LLM-based routing vs fallback logic
- Multi-agent coordination

**Query Analyzer Agent Tests:**
- 5-step workflow integration
- Clarification workflow
- Session management
- Relevance checking

**Search Agent Tests:**
- Tavily API integration
- Search result processing
- Error handling for missing API keys
- LLM summarization of results

**Agent Controller Tests:**
- End-to-end query processing
- Session lifecycle management
- Error handling

The tests demonstrate:
- Basic query processing
- Clarification workflow
- Multi-agent coordination
- Session management

## Search Agent Features

### Real-Time Information Access
The search agent provides access to current information that may not be available in local knowledge bases:

- **Current Events**: Latest news and developments
- **Market Data**: Stock prices, financial information
- **Technology Updates**: Recent software releases, API changes
- **Research Papers**: Latest academic publications
- **Product Information**: Current specifications and availability

### Step-Back Question Enhancement
When the query analyzer generates step-back questions to provide broader context:

1. System detects step-back questions in analysis results
2. Interactive demo offers to search for these questions
3. Each question is searched automatically via Tavily API
4. Results are summarized using the LLM
5. Enhanced context improves final answer quality

### Search Integration Benefits
- **Complementary to RAG**: Combines local knowledge with web information
- **Current Information**: Overcomes knowledge cutoff limitations
- **Broad Context**: Step-back questions provide background information
- **User Control**: Users decide when to use search functionality
- **Error Handling**: Graceful degradation when search unavailable

## Integration Points

### With Existing Modules
- **Query Analyzer**: Direct integration via QueryAnalyzerAgent wrapper
- **Storage Manager**: Future integration via RAGAgent
- **Embeddings**: Future integration via RAGAgent
- **PDF Processor**: Future integration via RAGAgent

### With External Systems
- **Tavily Search API**: Real-time web search capabilities
- **MCP Servers**: Future integration via MCPAgent
- **APIs**: Via MCP protocol
- **Tools**: Via MCP tool execution

## Future Development

### RAG Integration
```python
# Future RAGAgent implementation
rag_agent = RAGAgent(
    storage_manager=ChromaManager(),
    embeddings_model=CLIPEmbeddings()
)
```

### MCP Integration
```python
# Future MCPAgent implementation
mcp_agent = MCPAgent(
    mcp_server_urls=[
        "http://localhost:8080/maintenance-tools",
        "http://localhost:8081/calculation-tools"
    ]
)
```

## Configuration

Environment variables:
```bash
# LLM Configuration using local Ollama

# Agent Configuration
AGENT_LLM_MODEL=llama3.2  # Default Ollama model
AGENT_ENABLE_RAG=true
AGENT_ENABLE_MCP=true
AGENT_ENABLE_SEARCH=true

# Search Configuration
TAVILY_API_KEY=your-api-key-here  # Required for search functionality
TAVILY_MAX_RESULTS=5  # Optional: max search results
TAVILY_SEARCH_DEPTH=advanced  # Optional: search depth

# Logging
AGENT_LOG_LEVEL=INFO
```

## Error Handling

The system includes comprehensive error handling:
- Agent-level error recovery
- Graceful degradation
- Session state preservation
- Detailed error logging

## Testing

```bash
# Run agent tests
pytest tests/agent/

# Run integration tests
pytest tests/integration/test_agent_system.py
```

## Monitoring

Built-in monitoring capabilities:
- Agent decision tracking
- Performance metrics
- Session analytics
- Error reporting

## Acknowledgments

Built using:
- **LangGraph**: Agent coordination and workflow management
- **LangChain**: LLM integration and tool interfaces
- **Existing Query Analyzer**: Query understanding and clarification