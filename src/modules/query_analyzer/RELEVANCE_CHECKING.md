# Contextual Relevance Checking for Query Analysis

## Overview

The contextual relevance checking feature enhances the query analyzer to assess whether user queries are relevant to the domain context stored in the vector database. This helps improve efficiency by identifying out-of-context queries early in the pipeline, avoiding unnecessary processing and providing better user feedback.

## Key Features

### Evaluation Modes

The relevance checker supports two evaluation modes that can be configured via the `evaluation_mode` parameter:

#### 1. Two-Stage Relevance Assessment (Default: `evaluation_mode="two_stage"`)

1. **Fast Pre-filter (Stage 1)**
   - Domain vocabulary matching
   - Technical pattern recognition (part numbers, measurements, references)
   - Query type indicators
   - Negative indicator detection
   - Minimal computational cost

2. **Semantic Validation (Stage 2)**
   - Embedding-based similarity comparison
   - Comparison against representative domain embeddings
   - Higher accuracy but more computationally expensive
   - Only triggered for queries with medium confidence

#### 2. Task-Action-Target Assessment (`evaluation_mode="task_action_target"`)

This mode uses **LLM-based evaluation** with instructions from `technical_tasks_evaluate.txt` to assess queries for:
- **Task Actions**: Technical verbs (e.g., "remove", "install", "adjust", "inspect")
- **Target Objects**: Equipment or component names (e.g., "filter", "bolt", "engine", "brake")

**Key characteristics:**
- **Requires LLM provider** (e.g., Ollama with llama3.2)
- Uses structured prompt template for consistent evaluation
- Query must contain BOTH an action and a target to be considered relevant
- Provides contextual suggestions for missing components
- Ideal for technical task-oriented systems
- Returns domain matches in format: `["action:remove", "target:filter"]`
- Fallback to rule-based evaluation if LLM fails

### Configuration Options

```python
from src.modules.query_analyzer.models import RelevanceConfig

relevance_config = RelevanceConfig(
    enabled=True,                          # Enable/disable relevance checking
    evaluation_mode="two_stage",           # "two_stage" or "task_action_target"
    min_domain_terms=1,                    # Minimum domain terms for relevance
    high_confidence_threshold=0.8,         # Threshold for high confidence
    low_confidence_threshold=0.3,          # Threshold for low confidence
    enable_semantic_validation=True,       # Enable semantic stage (two_stage mode)
    semantic_threshold=0.5,                # Similarity threshold for semantic
    rejection_mode="soft",                 # "hard", "soft", or "score"
    domain_vocabulary_path="./config/domain_vocabulary.json",
    domain_patterns_path="./config/domain_patterns.json",
    task_action_prompt_path="./config/technical_tasks_evaluate.txt",
    task_action_model_name="llama3.2",    # LLM model for task-action-target mode
    task_action_temperature=0.0           # Temperature for deterministic output
)
```

### Rejection Modes

The `rejection_mode` parameter in `RelevanceConfig` determines how the system handles queries that are deemed irrelevant to your domain context. There are three modes available:

#### **hard** mode
- **Behavior**: Immediately rejects irrelevant queries and returns empty results without further processing
- **Use case**: Best for production environments where you want strict filtering and don't want to waste computational resources on out-of-context queries
- **Effect**: 
  - Query analyzer returns early with `query_type="out_of_context"`
  - Retrieval operations return empty results list
  - Minimal processing overhead for irrelevant queries
- **Example scenario**: A technical documentation system that should only answer automotive repair questions, rejecting queries about cooking or weather

#### **soft** mode (default)
- **Behavior**: Warns about potential irrelevance but continues processing the query anyway
- **Use case**: Ideal for development/testing or when you want a user-friendly experience that still attempts to help even with borderline queries
- **Effect**: 
  - Shows warning messages in console output
  - Proceeds with normal search and retrieval
  - May return results even if confidence is low
  - Includes suggestions for better queries if available
- **Example scenario**: A customer support system that primarily handles technical queries but occasionally needs to address tangential topics

#### **score** mode
- **Behavior**: Always processes queries normally but provides relevance scoring information
- **Use case**: Perfect for analytics, monitoring, or when you want to track relevance metrics without affecting user experience
- **Effect**: 
  - Includes relevance information in results metadata
  - No blocking or warning messages
  - Full query processing regardless of relevance score
  - Useful for collecting data on query patterns
- **Example scenario**: A system in early deployment where you want to understand what users are asking before implementing stricter filtering

## Usage Examples

### Basic Usage with Query Analyzer

```python
from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import QueryAnalyzerConfig, RelevanceConfig
from src.modules.embeddings.factory import EmbedderFactory

# Configure analyzer and relevance checking
analyzer_config = QueryAnalyzerConfig(model_name="llama3.2")
relevance_config = RelevanceConfig(enabled=True, rejection_mode="soft")

# Create components
embedder = EmbedderFactory.create("clip")
analyzer = OllamaQueryAnalyzer(analyzer_config, relevance_config)
relevance_checker = ContextualRelevanceChecker(relevance_config, embedder)
analyzer.set_relevance_checker(relevance_checker)

# Analyze query
intent = analyzer.analyze("How to replace brake pads?")

# Check relevance
if intent.relevance_info:
    print(f"Relevant: {intent.relevance_info.is_relevant}")
    print(f"Confidence: {intent.relevance_info.confidence:.2%}")
    print(f"Explanation: {intent.relevance_info.explanation}")
```

### Task-Action-Target Mode Usage

```python
from langchain_ollama import ChatOllama

# Create LLM provider for task-action-target evaluation
llm = ChatOllama(
    model="llama3.2",
    temperature=0.0
)

# Configure for task-action-target evaluation
relevance_config = RelevanceConfig(
    enabled=True,
    evaluation_mode="task_action_target",
    rejection_mode="soft"
)

# Create checker with LLM provider
relevance_checker = ContextualRelevanceChecker(relevance_config, llm_provider=llm)

# Example queries and their evaluations
queries = {
    "remove the oil filter": {
        "relevant": True,
        "confidence": 1.0,
        "matches": ["action:remove", "target:oil filter"]
    },
    "the engine": {
        "relevant": False,
        "confidence": 0.3,
        "suggestions": ["Specify what you want to do with the engine"]
    },
    "tighten": {
        "relevant": False,
        "confidence": 0.5,
        "suggestions": ["Specify the component (e.g., 'brake pads', 'oil filter')"]
    }
}

for query in queries:
    result = relevance_checker.check_relevance(query)
    print(f"Query: '{query}'")
    print(f"  Relevant: {result.is_relevant}")
    print(f"  Stage: {result.stage}")  # Will show "task-action-target"
    print(f"  Explanation: {result.explanation}")
```

### Usage with Enhanced Retriever

```python
from src.modules.query_analyzer.enhanced_retriever import EnhancedRetriever

retriever = EnhancedRetriever(
    storage_manager=storage_manager,
    embedder=embedder,
    query_analyzer=analyzer,
    relevance_config=relevance_config
)

# Retriever will automatically check relevance before searching
results = retriever.retrieve("What's the weather today?")
# Will show warning about out-of-context query
```

### Using the Factory

```python
from src.modules.query_analyzer.factory import QueryAnalyzerFactory

analyzer = QueryAnalyzerFactory.create(
    implementation="ollama",
    relevance_config=RelevanceConfig(enabled=True),
    embedder=embedder
)
```

## Domain Configuration

### Domain Vocabulary

The system uses a domain vocabulary file (`config/domain_vocabulary.json`) containing categorized technical terms:

```json
{
  "technical_terms": ["engine", "transmission", "brake", ...],
  "component_names": ["cylinder", "piston", "valve", ...],
  "actions": ["install", "remove", "replace", ...],
  "measurements": ["torque", "pressure", "temperature", ...]
}
```

### Domain Patterns

Technical patterns are defined in `config/domain_patterns.json`:

```json
{
  "part_number": "[A-Z0-9]{2,}-[A-Z0-9]{2,}(?:-[A-Z0-9]+)*",
  "measurement": "\\d+\\.?\\d*\\s*(mm|cm|psi|bar|°C|°F|...)",
  "reference": "(?:figure|table|section|step)\\s+\\d+",
  ...
}
```

## Choosing Between Evaluation Modes

### When to Use Two-Stage Mode (Default)

Use `evaluation_mode="two_stage"` when:
- You need comprehensive domain coverage beyond just task-based queries
- Your system handles various query types (questions, statements, comparisons)
- You want to leverage semantic similarity for nuanced relevance decisions
- You have representative embeddings for your domain

**Examples of queries better suited for two-stage:**
- "What is the torque specification for cylinder head bolts?"
- "Compare disc brakes vs drum brakes"
- "Engine overheating symptoms"

### When to Use Task-Action-Target Mode

Use `evaluation_mode="task_action_target"` when:
- Your system primarily handles technical task instructions
- You need explicit action-object validation with LLM intelligence
- You want contextual feedback about missing query components
- Your domain is heavily procedure/task-oriented
- You have access to an LLM for nuanced evaluation

**Examples of queries better suited for task-action-target:**
- "Remove the oil filter"
- "Install new brake pads"
- "Adjust valve clearance"

**Requirements:**
- LLM provider (e.g., Ollama with llama3.2)
- Structured prompt template (technical_tasks_evaluate.txt)

## Customization

### Adding Custom Domain Terms

1. Edit `config/domain_vocabulary.json` to add domain-specific terms
2. Reload the relevance checker or restart the application

### Creating Custom Patterns

1. Add regex patterns to `config/domain_patterns.json`
2. Patterns should match technical content specific to your domain

### Extending for New Domains

```python
# Create domain-specific vocabulary
automotive_vocab = {
    "technical_terms": ["engine", "brake", ...],
    "component_names": ["piston", "valve", ...]
}

# Save to custom path
with open("config/automotive_vocabulary.json", "w") as f:
    json.dump(automotive_vocab, f)

# Use custom vocabulary
relevance_config = RelevanceConfig(
    domain_vocabulary_path="./config/automotive_vocabulary.json"
)
```

## Performance Considerations

1. **Caching**: Relevance checks are cached per query to avoid repeated computation
2. **Lazy Loading**: Representative embeddings are loaded only when needed
3. **Early Exit**: High/low confidence queries skip semantic validation
4. **Configurable**: Disable semantic validation for faster processing

## Testing

Run the test suite:

```bash
pytest tests/query_analyzer/test_relevance_checker.py -v
```

Run the examples:

```bash
# Basic relevance checking demo
python -m src.modules.query_analyzer.example_relevance

# Updated simple usage demo with relevance
python -m src.modules.query_analyzer.simple_usage_demo
```

## Best Practices

1. **Start with Pre-filter Only**: Begin with semantic validation disabled and enable if needed
2. **Tune Thresholds**: Adjust confidence thresholds based on your domain requirements
3. **Monitor False Negatives**: Use soft rejection mode initially to identify valid queries being marked irrelevant
4. **Update Vocabulary**: Regularly update domain vocabulary based on user queries
5. **Balance Performance**: Use semantic validation only when pre-filter confidence is uncertain

## Future Enhancements

1. **Dynamic Vocabulary Learning**: Automatically learn domain terms from stored documents
2. **Multi-Domain Support**: Support multiple domains with different vocabularies
3. **User Feedback Integration**: Learn from user feedback on relevance decisions
4. **Confidence Calibration**: Auto-tune confidence thresholds based on performance