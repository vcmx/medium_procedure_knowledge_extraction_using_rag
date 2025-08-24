# Query Analyzer Test Updates

## Overview

This document describes the updates made to the query analyzer test suite to support the new conversational flow features.

## Test Files Updated

### 1. Import Path Fixes

The following test files had their import paths corrected to work with the project structure:

### 2. New Test Features Added

#### test_single_query.py
Added two new test functions to demonstrate conversational capabilities:

- **`test_conversational_context()`**: Tests multi-turn conversations with context preservation
  - Demonstrates how follow-up queries use context from previous queries
  - Shows session management and summary features
  - Tests the `analyze_with_context()` method directly

- **`test_user_level_adaptation()`**: Tests how the system adapts to different user expertise levels
  - Compares query expansions for NOVICE vs EXPERT users
  - Demonstrates adaptive behavior based on user level

### 3. New Test Files Created

#### test_conversational_flow.py
Comprehensive test suite for the conversational flow components:
- Tests for `ConversationState` class
- Tests for `ConversationManager` class  
- Tests for `ConversationalWorkflow` orchestrator
- Mock-based tests for isolated component testing

#### test_conversational_storage_integration.py
Integration tests that combine conversational flow with storage/retrieval:
- **`test_conversational_retrieval_integration()`**: Full end-to-end test
  - Sets up temporary storage with test documents
  - Processes multiple related queries in a session
  - Demonstrates context-aware retrieval
  - Tests relevance checking and query rejection

- **`test_clarification_with_retrieval()`**: Tests clarification flow
  - Simulates user responses to clarifying questions
  - Shows how clarified queries improve retrieval accuracy
  - Demonstrates the clarification → retrieval pipeline

## Running the Updated Tests

### Individual Test Files

```bash
# Test basic functionality with conversational context
python tests/query_analyzer/test_single_query.py


# Test conversational flow components
pytest tests/query_analyzer/test_conversational_flow.py -v

# Test integration with storage
python tests/query_analyzer/test_conversational_storage_integration.py
```

### Run All Query Analyzer Tests

```bash
pytest tests/query_analyzer/ -v
```

## Key Testing Patterns

### 1. Session-Based Testing
```python
session_id = "test_session_123"
result1 = manager.process_query("First query", session_id)
result2 = manager.process_query("Follow-up query", session_id)
```

### 2. Context-Aware Analysis
```python
context = "Previous discussion about diesel engines"
intent = analyzer.analyze_with_context("What about maintenance?", context)
```

### 3. Clarification Simulation
```python
responses = {
    "What type of engine?": "Diesel",
    "What vehicle?": "Truck"
}
result = manager.process_query(query, session_id, user_responses=responses)
```

### 4. User Level Adaptation
```python
manager.update_user_level(session_id, UserLevel.EXPERT)
result = manager.process_query(query, session_id)
```

## Backward Compatibility

All changes maintain backward compatibility:
- Existing tests continue to work unchanged
- New features are opt-in through configuration
- Original `analyze()` method still works without context

## Dependencies

The conversational tests may require:
- `pytest` for unit tests
- `unittest.mock` for mocking
- Ollama running locally for integration tests
- Temporary storage directories for integration tests

## Best Practices for New Tests

1. **Use session IDs** for any conversational test
2. **Clean up resources** (especially temporary storage) in finally blocks
3. **Mock external dependencies** for unit tests
4. **Test edge cases** like empty context, session expiry, etc.
5. **Document test purpose** with clear docstrings

## Troubleshooting

### Import Errors
- Ensure the test file adds the project root to sys.path:
  ```python
  sys.path.insert(0, str(Path(__file__).parent.parent.parent))
  ```

### Ollama Connection Errors
- Ensure Ollama is running: `ollama serve`
- Check the model is available: `ollama list`

### Storage Permission Errors  
- Use `tempfile.mkdtemp()` for temporary test storage
- Always clean up with `shutil.rmtree()`