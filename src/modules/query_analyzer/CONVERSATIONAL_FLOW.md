# Conversational Query Analysis Flow

## Overview

The query analyzer now supports a natural conversational flow that builds context progressively through multiple interaction steps. This is a significant enhancement from the previous single-pass analysis approach.

## Architecture

### Core Components

1. **ConversationState**: Manages session state across multiple turns
2. **ConversationManager**: Orchestrates the 5-step conversational flow
3. **ConversationalWorkflow**: High-level workflow orchestrator for demonstrations

### The 5-Step Flow

```
1. User Initial Prompt
   ↓
2. Relevance Check → [Reject if irrelevant]
   ↓
3. Clarification Assessment → [Interactive clarification if needed]
   ↓
4. Intent Analysis (with context)
   ↓
5. Query Enhancement (stepback, expansion, decomposition)
```

## Key Differences from Single-Pass Approach

### Previous Approach (Single-Pass)
- All analysis features executed simultaneously
- No conversation memory
- Each query processed independently
- Clarification optional and one-time only

### New Approach (Conversational)
- Progressive context building
- Session-based conversation tracking
- Context-aware analysis
- Multi-round clarification possible
- Adaptive based on user level

## Usage Examples

### Basic Usage

```python
from src.modules.query_analyzer.conversational_workflow import ConversationalWorkflow
from src.modules.query_analyzer.conversation_state import UserLevel

# Create workflow
workflow = ConversationalWorkflow(
    analyzer_type="ollama",
    enable_relevance_check=True,
    enable_clarification=True
)

# Process a query
result, metadata = workflow.process_user_query(
    query="How do I fix the engine problem?",
    session_id="user_123",
    user_level=UserLevel.NOVICE
)

# Check results
if result.rejection_reason:
    print(f"Query rejected: {result.rejection_reason}")
else:
    print(f"Intent: {result.intent.semantic_intent}")
    print(f"Entities: {result.intent.entities}")
```

### Using ConversationManager Directly

```python
from src.modules.query_analyzer.conversation_manager import ConversationManager
from src.modules.query_analyzer.factory import create_query_analyzer

# Setup
analyzer = create_query_analyzer("ollama")
manager = ConversationManager(
    query_analyzer=analyzer,
    enable_clarification=True
)

# First query
result1 = manager.process_query(
    "Tell me about diesel engines",
    session_id="session_1"
)

# Follow-up query (uses context from previous query)
result2 = manager.process_query(
    "What about their maintenance?",  # "their" refers to diesel engines
    session_id="session_1"
)
```

### Interactive Clarification

```python
# Request clarification
clarification_request = manager.request_clarification(
    "Fix engine problem",
    session_id="session_1"
)

# Display questions to user
for question in clarification_request.questions:
    print(f"Q: {question}")

# Process user responses
responses = {
    "What type of engine?": "Diesel",
    "What specific problem?": "Won't start in cold weather"
}

result = manager.process_clarification_response(
    session_id="session_1",
    responses=responses
)
```

## ConversationState Features

### State Tracking
- **Entities**: Accumulates all entities mentioned across turns
- **Topics**: Tracks topics discussed
- **Clarifications**: Stores Q&A pairs for reference
- **User Level**: Adapts responses based on expertise

### Context Building
The `build_context_prompt()` method creates a context summary including:
- Recent conversation turns (last 3)
- Entities mentioned
- Clarifications made
- Current domain and task type
- User expertise level

### Example Context Prompt
```
Recent conversation:
- User: Tell me about diesel engines
  Intent: Understanding diesel engines
- User: What about maintenance?
  Intent: Diesel engine maintenance procedures

Entities discussed: diesel, engine, maintenance
Clarifications made:
- Q: Are you interested in preventive or corrective maintenance?
  A: Preventive maintenance

Current domain: automotive
Task type: explanation
User level: novice
```

## Implementation Details

### Session Management
Sessions are managed in-memory by default. For production use, consider:
- Redis for distributed session storage
- Database persistence for long-term history
- Session expiration policies

### Relevance Checking Integration
The flow integrates with the existing relevance checker:
- Stage 1: Vocabulary/pattern matching
- Stage 2: Semantic similarity (if needed)
- Early rejection for clearly irrelevant queries

### Query Enhancement with Context
Context influences query enhancement:
- **Expert users**: More technical expansions added
- **Novice users**: Simpler explanations prioritized
- **Entity context**: Previous entities referenced in expansions

## Configuration

### Enable Conversational Features
```python
# In query analyzer config
config = QueryAnalyzerConfig(
    enable_clarification=True,
    max_clarifying_questions=3
)

# In conversation manager
manager = ConversationManager(
    enable_clarification=True,
    max_clarification_rounds=2
)
```

### User Level Adaptation
```python
# Set user level for session
manager.update_user_level(session_id, UserLevel.EXPERT)

# Query processing will adapt:
# - More technical details for experts
# - Simpler explanations for novices
# - Different clarification strategies
```

## Benefits

1. **Natural Interaction**: Users can refine queries through conversation
2. **Context Preservation**: Follow-up questions work naturally
3. **Progressive Understanding**: System builds understanding over time
4. **Better Accuracy**: Clarifications lead to more precise retrieval
5. **User Adaptation**: Adjusts to user's expertise level

## Testing

Run the conversational flow tests:
```bash
pytest tests/query_analyzer/test_conversational_flow.py -v
```

Run the demonstration:
```python
python -m src.modules.query_analyzer.conversational_workflow
```

## Future Enhancements

1. **Anaphora Resolution**: Better handling of pronouns (it, that, etc.)
2. **Multi-modal Context**: Include image/document context
3. **Learning from Feedback**: Improve based on user satisfaction
4. **Conversation Summarization**: Generate summaries of long conversations
5. **Intent Prediction**: Anticipate user needs based on patterns

## Migration Guide

To migrate from single-pass to conversational:

1. Replace direct `QueryAnalyzer.analyze()` calls with `ConversationManager.process_query()`
2. Add session ID management to your application
3. Implement clarification UI if using interactive clarification
4. Consider user level tracking for better adaptation

Example migration:
```python
# Before (single-pass)
analyzer = create_query_analyzer("ollama")
intent = analyzer.analyze(query)

# After (conversational)
manager = ConversationManager(query_analyzer=analyzer)
result = manager.process_query(query, session_id="user_123")
intent = result.intent
```