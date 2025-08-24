"""Ollama-based implementation of query analyzer."""

import json
import logging
from typing import Callable, Dict, List, Optional

from .base import BaseQueryAnalyzer, QueryIntent
from .models import QueryAnalyzerConfig, QueryType, RelevanceConfig, RelevanceResult
from .relevance_checker import ContextualRelevanceChecker

logger = logging.getLogger(__name__)


class OllamaQueryAnalyzer(BaseQueryAnalyzer):
    """Query analyzer using Ollama for local LLM inference."""

    def __init__(
        self,
        config: Optional[QueryAnalyzerConfig] = None,
        relevance_config: Optional[RelevanceConfig] = None,
    ):
        """Initialize the Ollama query analyzer."""
        self.config = config or QueryAnalyzerConfig()
        self.relevance_config = relevance_config or RelevanceConfig()
        self.relevance_checker = None

        # Lazy import to make Ollama optional
        try:
            from langchain_core.output_parsers import PydanticOutputParser
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.runnables import RunnablePassthrough
            from langchain_ollama import ChatOllama

            # Store RunnablePassthrough as instance variable to use later
            self.RunnablePassthrough = RunnablePassthrough
        except ImportError:
            raise ImportError(
                "Ollama dependencies not installed. "
                "Please install with: pip install langchain-ollama"
            )

        self.llm = ChatOllama(
            model=self.config.model_name, temperature=self.config.temperature
        )

        # Create pydantic model for parsing
        from typing import Literal

        from pydantic import BaseModel, Field

        class QueryIntentModel(BaseModel):
            query_type: Literal[
                "factual", "comparison", "aggregation", "explanation"
            ] = Field(description="The type of query being asked")
            entities: List[str] = Field(
                default_factory=list, description="Key entities mentioned in the query"
            )
            time_filter: Optional[str] = Field(
                default=None, description="Any time-based constraints in the query"
            )
            semantic_intent: str = Field(
                description="The core intent of what the user is trying to find"
            )
            expanded_queries: List[str] = Field(
                default_factory=list,
                description="Alternative phrasings or expanded versions of the query",
            )

        self.parser = PydanticOutputParser(pydantic_object=QueryIntentModel)
        self.QueryIntentModel = QueryIntentModel

        # Build dynamic prompt based on enabled features
        prompt_parts = [
            "You are a query analysis expert. Analyze the user's query and extract:"
        ]
        prompt_parts.append(
            "1. The type of query (factual, comparison, aggregation, or explanation)"
        )

        prompt_idx = 2
        if self.config.enable_entity_extraction:
            prompt_parts.append(f"{prompt_idx}. Key entities mentioned")
            prompt_idx += 1

        if self.config.enable_time_filter:
            prompt_parts.append(f"{prompt_idx}. Any time-based filters")
            prompt_idx += 1

        prompt_parts.append(
            f"{prompt_idx}. The semantic intent - what the user really wants to know"
        )
        prompt_idx += 1

        if self.config.enable_query_expansion:
            prompt_parts.append(
                f"{prompt_idx}. Expanded queries - alternative ways to phrase the query for better retrieval"
            )

        prompt_parts.append("""
IMPORTANT: Return a JSON object with actual data values, NOT a schema.

Example of what to return:
{{
  "query_type": "explanation",
  "entities": ["jet engine", "compressor"],
  "time_filter": null,
  "semantic_intent": "How jet engine compressors work",
  "expanded_queries": ["How do jet engine compressors function?", "Explain jet engine compressor operation"]
}}

Do NOT return a schema like {{"properties": {{...}}}}. Return actual data values.
Do NOT wrap in markdown code blocks.
Your response must be pure JSON that can be parsed directly.

{{format_instructions}}""")

        self.prompt = ChatPromptTemplate.from_messages(
            [("system", "\n".join(prompt_parts)), ("human", "{query}")]
        )

        # Create simplified format instructions that work better with Llama
        simplified_format = """Return a JSON object with these exact fields:
- query_type: must be one of "factual", "comparison", "aggregation", or "explanation"
- entities: array of key entities/terms from the query
- time_filter: any time constraints (or null)
- semantic_intent: what the user wants to know
- expanded_queries: array of alternative phrasings"""

        # Don't use the parser in the chain - we'll parse manually
        self.chain = (
            {
                "query": self.RunnablePassthrough(),
                "format_instructions": lambda _: simplified_format,
            }
            | self.prompt
            | self.llm
        )

        # Create decomposition prompt and chain
        self.decomposition_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert at breaking down complex queries into sub-questions.

Given a query and its expanded versions, decompose them into atomic sub-questions that:
1. Can be answered independently
2. Are meaningful and relevant to the main query
3. Cover different aspects of the original question
4. Avoid duplication or redundancy
5. Are ordered from most fundamental to most complex

Return ONLY a JSON array of sub-questions. Each question should be self-contained.

Example:
Query: "How does the fuel injection system affect engine performance in cold weather?"
Expanded: ["What is the relationship between fuel injection and engine performance?", "Cold weather impact on fuel injection systems"]

Output: [
  "What is a fuel injection system?",
  "How does a fuel injection system work?",
  "What are the key components of engine performance?",
  "How does cold weather affect fuel properties?",
  "What changes occur in fuel injection during cold weather?",
  "How do these changes impact engine performance metrics?"
]""",
                ),
                (
                    "human",
                    "Query: {query}\nExpanded queries: {expanded_queries}\n\nDecompose into sub-questions:",
                ),
            ]
        )

        self.decomposition_chain = self.decomposition_prompt | self.llm

        # Create step-back prompt and chain
        self.step_back_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert at abstracting specific questions into more general, higher-level questions.

Given a specific query, generate step-back questions that:
1. Are more general and abstract than the original
2. Cover the underlying concepts or principles
3. Are easier to find comprehensive information about
4. Help understand the broader context
5. Remove specific details while preserving the core intent

Return ONLY a JSON array of 2-4 step-back questions, ordered from most general to more specific.

Examples:
Query: "Why does my 2019 Honda Civic make a grinding noise when braking at low speeds?"
Step-back: [
  "What are common causes of brake noise in vehicles?",
  "How do automotive braking systems work?",
  "What are typical brake problems and their symptoms?"
]

Query: "How to fix Python TypeError when concatenating string and integer in version 3.9?"
Step-back: [
  "What are Python data types and type conversion?",
  "How does Python handle different data types in operations?",
  "What are common Python type errors and their solutions?"
]""",
                ),
                ("human", "Query: {query}\n\nGenerate step-back questions:"),
            ]
        )

        self.step_back_chain = self.step_back_prompt | self.llm

        # Create clarifying questions prompt and chain
        self.clarifying_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an assistant that helps users clarify their queries based on the technical manuals you have access to. Your primary goal is to determine which manual the user's query refers to.

**Available Manuals:**
{document_summaries_context}

Analyze the user's query. If the query is generic and could apply to more than one of the available manuals, your FIRST question MUST be to ask the user to specify which manual they are interested in.

If the query is already specific to one manual (e.g., it mentions "Subaru"), or if there is only one manual available, you can ask other clarifying questions about the problem itself.

If the query is very specific and needs no clarification, return an empty JSON array.

You MUST return a JSON array of strings.

---
**Example 1: Generic Query, Multiple Manuals**
*Query:* "How do I change the oil?"
*Your Response:* [
    "Which vehicle are you asking about? I have manuals for: Subaru Outback, Yamaha Tenere.",
    "Which manual are you referring to?",
    "Which systems are you referring to?",
]
---
**Example 2: No Clarification Needed**
*Query:* "What is the oil capacity for a 2020 Subaru Outback?"
*Your Response:* []
---
""",
                ),
                ("human", "Query: {query}\n\nResponse:"),
            ]
        )

        self.clarifying_chain = (
            {
                "query": self.RunnablePassthrough(),
                "document_summaries_context": self.RunnablePassthrough(),
            }
            | self.clarifying_prompt
            | self.llm
        )

        # Create query rephrasing prompt and chain
        self.rephrase_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert at rephrasing queries with additional context to make them clearer and more specific.

Given an original query and clarifying context from the user, rephrase the query to:
1. Include all relevant context provided
2. Be more specific and unambiguous
3. Maintain the original intent
4. Be self-contained (someone reading only the rephrased query should understand the full context)
5. Be natural and well-structured

Return ONLY the rephrased query as a single string, not JSON.

Example:
Original query: "How to fix the error?"
Context:
- Error message: "TypeError: cannot concatenate str and int"
- Language: Python 3.9
- Trying to: Build a string with user ID
- Tried: str() conversion but it didn't work

Rephrased query: "How to fix Python 3.9 TypeError 'cannot concatenate str and int' when trying to build a string with user ID, where str() conversion doesn't resolve the issue?"
""",
                ),
                (
                    "human",
                    "Original query: {query}\n\nClarifying context:\n{context}\n\nRephrase the query with the additional context:",
                ),
            ]
        )

        self.rephrase_chain = self.rephrase_prompt | self.llm

    def _decompose_query(self, query: str, expanded_queries: List[str]) -> List[str]:
        """Decompose a query into sub-questions."""
        if not self.config.enable_decomposition:
            return []

        try:
            response = self.decomposition_chain.invoke(
                {"query": query, "expanded_queries": expanded_queries}
            )

            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Parse JSON array using our robust extraction method
            sub_questions = self._extract_json_array_from_content(content)

            if isinstance(sub_questions, list):
                # Deduplicate while preserving order
                seen_normalized = set()
                unique_questions = []

                for q in sub_questions:
                    # Normalize for comparison (lowercase, strip whitespace)
                    normalized = q.lower().strip()

                    # Skip if too similar to existing questions
                    if not any(
                        self._is_similar_question(normalized, existing)
                        for existing in seen_normalized
                    ):
                        seen_normalized.add(normalized)
                        unique_questions.append(q.strip())

                print(f"  ✓ Decomposed into {len(unique_questions)} sub-questions")
                return unique_questions[: self.config.max_decomposed_questions]

            return []

        except Exception as e:
            print(f"  ⚠️  Decomposition failed: {str(e)}")
            return []

    def _is_similar_question(self, q1: str, q2: str) -> bool:
        """Check if two questions are similar enough to be considered duplicates."""
        # Remove common question words for comparison
        stopwords = {
            "what",
            "how",
            "why",
            "when",
            "where",
            "which",
            "who",
            "is",
            "are",
            "does",
            "do",
            "the",
            "a",
            "an",
        }

        words1 = set(q1.split()) - stopwords
        words2 = set(q2.split()) - stopwords

        # If either set is empty after removing stopwords, fall back to exact match
        if not words1 or not words2:
            return q1 == q2

        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        similarity = len(intersection) / len(union) if union else 0

        # Consider similar if more than 70% overlap
        return similarity > 0.7

    def _generate_step_back_questions(self, query: str) -> List[str]:
        """Generate step-back questions for the given query."""
        if not self.config.enable_step_back:
            return []

        try:
            response = self.step_back_chain.invoke({"query": query})

            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Parse JSON array using our robust extraction method
            if content.strip().startswith("["):
                step_back_questions = json.loads(content)
            else:
                step_back_questions = self._extract_json_array_from_content(content)

            if isinstance(step_back_questions, list):
                print(f"  ✓ Generated {len(step_back_questions)} step-back questions")
                return step_back_questions[: self.config.max_step_back_questions]

            return []

        except Exception as e:
            print(f"  ⚠️  Step-back generation failed: {str(e)}")
            return []

    def _generate_clarifying_questions(
        self, query: str, document_summaries: Optional[List[str]] = None
    ) -> List[str]:
        """Generate clarifying questions if the query is ambiguous."""
        if not self.config.enable_clarification:
            return []

        # Format document summaries for the prompt
        summaries_context = "No manuals available."
        if document_summaries:
            summaries_context = "\n".join([f"- {s}" for s in document_summaries])

        logger.info(
            f"[_generate_clarifying_questions] Generating with context: {summaries_context}"
        )

        try:
            # The chain now expects a dictionary for the input
            response = self.clarifying_chain.invoke(
                {"query": query, "document_summaries_context": summaries_context}
            )
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            logger.info(f"[_generate_clarifying_questions] Raw LLM content: {content}")

            questions = self._extract_json_array_from_content(content)

            logger.info(
                f"[_generate_clarifying_questions] Parsed questions: {questions}"
            )

            return questions
        except Exception as e:
            logger.error(
                f"Error generating clarifying questions for query '{query}': {e}"
            )
            return []

    def _rephrase_with_context(self, original_query: str, context: str) -> str:
        """Rephrase the query with additional context."""
        try:
            response = self.rephrase_chain.invoke(
                {"query": original_query, "context": context}
            )

            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Clean up the response
            rephrased = content.strip().strip('"').strip("'")

            print(f"  ✓ Rephrased query: '{rephrased}'")
            return rephrased

        except Exception as e:
            print(f"  ⚠️  Query rephrasing failed: {str(e)}")
            return original_query

    def clarify_interactively(
        self, query: str, response_collector: Optional[Callable[[str], str]] = None
    ) -> Dict[str, any]:
        """
        Generate clarifying questions and collect responses interactively.

        Args:
            query: The original query to clarify
            response_collector: Optional function to collect user responses.
                               If not provided, uses standard input.

        Returns:
            Dictionary with:
                - original_query: The original query
                - clarifying_questions: List of clarifying questions asked
                - responses: Dict mapping questions to responses
                - clarified_query: The rephrased query with context
        """
        print(f"\n🤔 Generating clarifying questions for: '{query}'")

        # Generate clarifying questions
        clarifying_questions = self._generate_clarifying_questions(query)

        if not clarifying_questions:
            print("  ℹ️  No clarifying questions needed")
            return {
                "original_query": query,
                "clarifying_questions": [],
                "responses": {},
                "clarified_query": query,
            }

        # Collect responses
        responses = {}
        print(
            "\n📋 Please answer the following questions to help me better understand your query:"
        )

        for i, question in enumerate(clarifying_questions, 1):
            print(f"\n{i}. {question}")

            if response_collector:
                response = response_collector(question)
            else:
                response = input("   Your answer: ").strip()

            if response:  # Only store non-empty responses
                responses[question] = response

        # Build context from responses
        context_parts = []
        for question, response in responses.items():
            # Extract the key part of the question for context
            context_parts.append(f"- {question}: {response}")

        context = "\n".join(context_parts)

        # Rephrase the query with context
        if context:
            clarified_query = self._rephrase_with_context(query, context)
        else:
            clarified_query = query

        return {
            "original_query": query,
            "clarifying_questions": clarifying_questions,
            "responses": responses,
            "clarified_query": clarified_query,
        }

    def set_relevance_checker(self, relevance_checker: ContextualRelevanceChecker):
        """Set the relevance checker for this analyzer."""
        self.relevance_checker = relevance_checker

    def check_relevance(self, query: str) -> Optional[RelevanceResult]:
        """Check if query is contextually relevant to the domain."""
        if self.relevance_checker and self.relevance_config.enabled:
            return self.relevance_checker.check_relevance(query)
        return None

    def analyze_with_context(
        self, query: str, context: Optional[str] = None
    ) -> QueryIntent:
        """
        Analyze a query with optional conversation context.

        Args:
            query: The query to analyze
            context: Optional conversation context (e.g., previous queries, entities, clarifications)

        Returns:
            QueryIntent with analysis results
        """
        # If context is provided, prepend it to the query for analysis
        if context:
            # Create a context-enhanced query for the LLM
            enhanced_query = f"{context}\n\nCurrent query: {query}"

            # Analyze the enhanced query
            intent = self.analyze(enhanced_query)

            # The semantic intent and other fields will reflect the context
            # Note: QueryIntent doesn't have raw_query field, but the enhanced analysis
            # will be reflected in the semantic_intent and other fields

            return intent
        else:
            # No context, use regular analysis
            return self.analyze(query)

    def analyze(self, query: str) -> QueryIntent:
        """Analyze a query and return structured intent."""
        print(f"\n🧠 Analyzing query: '{query}'")

        # Check relevance first if enabled
        relevance_result = None
        if self.relevance_config.enabled:
            relevance_result = self.check_relevance(query)

            if relevance_result:
                print(
                    f"  📊 Relevance check: {'✅ Relevant' if relevance_result.is_relevant else '❌ Out of context'}"
                )
                print(f"  📊 Confidence: {relevance_result.confidence:.2f}")
                print(f"  📊 Stage: {relevance_result.stage}")

                # If clearly irrelevant, return early with minimal processing
                if (
                    not relevance_result.is_relevant
                    and self.relevance_config.rejection_mode == "hard"
                ):
                    print("  ⚠️  Query rejected as out of context")
                    return QueryIntent(
                        query_type="out_of_context",
                        entities=[],
                        time_filter=None,
                        semantic_intent="Query is outside the technical documentation domain",
                        expanded_queries=[],
                        decomposed_questions=[],
                        step_back_questions=[],
                        clarifying_questions=[],
                        relevance_info=relevance_result,
                    )

        try:
            # Try the normal chain first
            response = self.chain.invoke(query)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Parse the JSON response
            data = self._extract_json_from_content(content)

            # Create model instance for validation
            try:
                result = self.QueryIntentModel(**data)
            except Exception as validation_error:
                # If validation fails, use the data directly with defaults
                print(f"  ⚠️  Model validation failed: {str(validation_error)[:100]}...")
                # Apply validation and fixes to data
                data = self._validate_and_fix_data(data)

                # Create a simple object to mimic the model
                class SimpleResult:
                    def __init__(self, data):
                        self.query_type = data.get("query_type", "factual")
                        self.entities = data.get("entities", [])
                        self.time_filter = data.get("time_filter", None)
                        self.semantic_intent = data.get("semantic_intent", "")
                        self.expanded_queries = data.get("expanded_queries", [])

                result = SimpleResult(data)

            # Convert to dataclass with feature flags
            intent = QueryIntent(
                query_type=result.query_type,
                entities=result.entities
                if self.config.enable_entity_extraction
                else [],
                time_filter=result.time_filter
                if self.config.enable_time_filter
                else None,
                semantic_intent=result.semantic_intent,
                expanded_queries=result.expanded_queries[
                    : self.config.max_expanded_queries
                ]
                if self.config.enable_query_expansion
                else [],
            )

            print(f"  ✓ Query type: {intent.query_type}")
            print(f"  ✓ Entities found: {intent.entities}")
            print(f"  ✓ Semantic intent: '{intent.semantic_intent}'")

            # Decompose the query into sub-questions
            intent.decomposed_questions = self._decompose_query(
                query, intent.expanded_queries
            )

            # Generate step-back questions
            intent.step_back_questions = self._generate_step_back_questions(query)

            return intent

        except Exception as e:
            # Fallback parsing logic
            print(f"  ⚠️  Initial parsing failed: {str(e)[:100]}...")
            print("  ⚠️  Trying fallback...")

            try:
                # Get raw response
                raw_response = (
                    {
                        "query": self.RunnablePassthrough(),
                        "format_instructions": lambda _: self.parser.get_format_instructions(),
                    }
                    | self.prompt
                    | self.llm
                ).invoke(query)

                content = (
                    raw_response.content
                    if hasattr(raw_response, "content")
                    else str(raw_response)
                )

                # Try to extract JSON
                if "properties" in content:
                    # Handle schema response (don't require "required" field)
                    print("  ✓ Detected schema format, extracting data...")
                    schema_dict = json.loads(content)
                    data = self._extract_data_from_schema(schema_dict)
                else:
                    # Try direct JSON parsing
                    data = self._extract_json_from_content(content)

                # Create model instance
                try:
                    result = self.QueryIntentModel(**data)
                except Exception as validation_error:
                    # If validation fails, use the data directly with defaults
                    print(
                        f"  ⚠️  Fallback model validation failed: {str(validation_error)[:100]}..."
                    )
                    # Apply validation and fixes to data
                    data = self._validate_and_fix_data(data)

                    # Create a simple object to mimic the model
                    class SimpleResult:
                        def __init__(self, data):
                            self.query_type = data.get("query_type", "factual")
                            self.entities = data.get("entities", [])
                            self.time_filter = data.get("time_filter", None)
                            self.semantic_intent = data.get("semantic_intent", "")
                            self.expanded_queries = data.get("expanded_queries", [])

                    result = SimpleResult(data)

                # Convert to dataclass with feature flags
                intent = QueryIntent(
                    query_type=result.query_type,
                    entities=result.entities
                    if self.config.enable_entity_extraction
                    else [],
                    time_filter=result.time_filter
                    if self.config.enable_time_filter
                    else None,
                    semantic_intent=result.semantic_intent,
                    expanded_queries=result.expanded_queries[
                        : self.config.max_expanded_queries
                    ]
                    if self.config.enable_query_expansion
                    else [],
                )

                print(f"  ✓ Fallback successful - Type: {intent.query_type}")

                # Decompose the query into sub-questions
                intent.decomposed_questions = self._decompose_query(
                    query, intent.expanded_queries
                )

                # Generate step-back questions
                intent.step_back_questions = self._generate_step_back_questions(query)

                return intent

            except:
                # Final fallback
                print("  ⚠️  Using basic fallback")
                return QueryIntent(
                    query_type=QueryType.FACTUAL,
                    entities=[],
                    time_filter=None,
                    semantic_intent=query,
                    expanded_queries=[query],
                    decomposed_questions=[],
                    step_back_questions=[],
                    clarifying_questions=[],
                    relevance_info=relevance_result,
                )

    def analyze_for_clarification_only(
        self, query: str, document_summaries: Optional[List[str]] = None
    ) -> QueryIntent:
        """
        Perform a lightweight analysis to generate only clarifying questions.

        This is useful for a preliminary check before a full analysis.
        """
        clarifying_questions = self._generate_clarifying_questions(
            query, document_summaries=document_summaries
        )

        return QueryIntent(
            query_type="clarification",
            semantic_intent="Needs clarification",
            clarifying_questions=clarifying_questions,
            entities=[],
            time_filter=None,
            expanded_queries=[],
            decomposed_questions=[],
            step_back_questions=[],
        )

    def analyze_with_clarification(
        self,
        query: str,
        response_collector: Optional[Callable[[str], str]] = None,
        auto_clarify: bool = True,
    ) -> QueryIntent:
        """
        Analyze a query with optional interactive clarification.

        Args:
            query: The query to analyze
            response_collector: Optional function to collect user responses
            auto_clarify: Whether to automatically clarify if questions are generated

        Returns:
            QueryIntent with clarified query if clarification was performed
        """
        # First, do initial analysis to check if clarification is needed
        initial_intent = self.analyze(query)

        # If no clarifying questions or auto_clarify is False, return as is
        if not auto_clarify or not initial_intent.clarifying_questions:
            return initial_intent

        # Perform interactive clarification
        clarification_result = self.clarify_interactively(query, response_collector)

        # If we got a clarified query, analyze it
        if clarification_result["clarified_query"] != query:
            print("\n🔄 Re-analyzing with clarified query...")
            clarified_intent = self.analyze(clarification_result["clarified_query"])

            # Preserve the original clarifying questions and clarified query
            clarified_intent.clarifying_questions = initial_intent.clarifying_questions
            clarified_intent.clarified_query = clarification_result["clarified_query"]

            return clarified_intent

        # If no clarification happened, return initial intent
        return initial_intent

    def get_retrieval_queries(self, query: str) -> List[str]:
        """Get optimized queries for retrieval based on analysis."""
        intent = self.analyze(query)

        # Start with original query
        queries = [query]

        # Add expanded queries
        queries.extend(intent.expanded_queries)

        # Add entity-focused queries if applicable
        if intent.entities:
            entity_query = f"{intent.semantic_intent} {' '.join(intent.entities)}"
            queries.append(entity_query)

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)

        return unique_queries

    def _extract_data_from_schema(self, schema_dict: dict) -> dict:
        """Extract default values from a Pydantic schema."""
        data = {}

        if "properties" in schema_dict:
            properties = schema_dict["properties"]

            # Extract meaningful data from schema properties
            for key, prop_def in properties.items():
                if isinstance(prop_def, dict):
                    # Try to extract actual data from the schema definition
                    if "default" in prop_def:
                        data[key] = prop_def["default"]
                    elif "title" in prop_def and key == "semantic_intent":
                        # Use title as semantic intent if it looks meaningful
                        data[key] = prop_def["title"]
                    elif "enum" in prop_def and key == "query_type":
                        # Use first enum value or infer from other data
                        data[key] = (
                            prop_def["enum"][0] if prop_def["enum"] else "factual"
                        )
                    elif prop_def.get("type") == "array":
                        # Initialize arrays as empty
                        data[key] = []
                    elif prop_def.get("type") == "string":
                        # Use title or description as default string value
                        data[key] = prop_def.get(
                            "title", prop_def.get("description", "")
                        )
                    else:
                        data[key] = None
                else:
                    data[key] = prop_def

        # Store schema title for later use (check both top level and inside properties)
        schema_title = schema_dict.get("title", "")
        if not schema_title and "title" in data:
            # LLM put title as a property instead of schema title
            schema_title = data["title"]
            # Remove title from data as it's not a real field
            del data["title"]
        if (
            not schema_title
            and "properties" in schema_dict
            and "title" in schema_dict["properties"]
        ):
            # Sometimes LLM puts title as a property definition
            title_prop = schema_dict["properties"]["title"]
            if isinstance(title_prop, str):
                schema_title = title_prop
            elif isinstance(title_prop, dict) and "title" in title_prop:
                schema_title = title_prop["title"]

        # Remove other schema artifacts from data
        if "type" in data and data["type"] == "object":
            del data["type"]

        # Try to infer semantic intent from schema title
        if schema_title and (
            not data.get("semantic_intent")
            or data.get("semantic_intent") in ["Semantic Intent", ""]
        ):
            data["semantic_intent"] = schema_title

        # Ensure required fields with better defaults
        if "query_type" not in data or not QueryType.is_valid(
            data.get("query_type", "")
        ):
            # Try to infer query type from semantic intent
            semantic_intent = data.get("semantic_intent", "").lower()
            if any(word in semantic_intent for word in ["how", "explain", "what is"]):
                data["query_type"] = QueryType.EXPLANATION
            elif any(
                word in semantic_intent for word in ["compare", "difference", "vs"]
            ):
                data["query_type"] = QueryType.COMPARISON
            else:
                data["query_type"] = QueryType.FACTUAL

        if (
            "semantic_intent" not in data
            or not data["semantic_intent"]
            or data["semantic_intent"] in ["Semantic Intent", ""]
        ):
            data["semantic_intent"] = schema_title

        if "entities" not in data:
            data["entities"] = []

        if "expanded_queries" not in data:
            data["expanded_queries"] = []

        # Apply validation to ensure data integrity
        return self._validate_and_fix_data(data)

    def _extract_json_array_from_content(self, content: str) -> list:
        """Extract JSON array from content that might be wrapped in markdown or other formatting."""
        import re

        # First try direct parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Check if it's a truncated array (missing closing bracket)
            if "Expecting ',' delimiter" in str(e) or "Expecting value" in str(e):
                # Try to fix truncated JSON array
                content_stripped = content.strip()
                if content_stripped.startswith("[") and not content_stripped.endswith(
                    "]"
                ):
                    # Add closing bracket and try again
                    try:
                        # First, check if we're in the middle of a string
                        # Count quotes to see if we have an unclosed string
                        quote_count = content_stripped.count('"')
                        if quote_count % 2 == 1:
                            # Odd number of quotes, we're in a string
                            content_fixed = content_stripped + '"]'
                        else:
                            # Even quotes, just add closing bracket
                            content_fixed = content_stripped + "]"
                        return json.loads(content_fixed)
                    except json.JSONDecodeError:
                        pass
            pass

        # Try to extract JSON array from markdown code blocks
        json_patterns = [
            r"```(?:json)?\s*\n?(.*?)\n?```",  # Standard markdown code blocks
            r"```\s*\n?(.*?)\n?```",  # Any code block
            r"\[.*\]",  # Any JSON array
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    # Clean up the match
                    cleaned = match.strip()
                    if cleaned and cleaned.startswith("["):
                        return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue

        # If no JSON array found, try to extract from content
        # Look for array start and end
        start_idx = content.find("[")
        if start_idx != -1:
            # Find matching closing bracket
            bracket_count = 0
            in_string = False
            escape_next = False

            for i in range(start_idx, len(content)):
                char = content[i]

                if escape_next:
                    escape_next = False
                    continue

                if char == "\\":
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == "[":
                        bracket_count += 1
                    elif char == "]":
                        bracket_count -= 1
                        if bracket_count == 0:
                            try:
                                return json.loads(content[start_idx : i + 1])
                            except json.JSONDecodeError:
                                break

        # If all fails, return empty array
        return []

    def _extract_json_from_content(self, content: str) -> dict:
        """Extract JSON from content that might be wrapped in markdown or other formatting."""
        import re

        # First try direct parsing
        try:
            data = json.loads(content)
            return self._validate_and_fix_data(data)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        # Look for ```json or ``` followed by JSON
        json_patterns = [
            r"```(?:json)?\s*\n?(.*?)\n?```",  # Standard markdown code blocks
            r"```\s*\n?(.*?)\n?```",  # Any code block
            r"\{.*\}",  # Any JSON-like object
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    # Clean up the match
                    cleaned = match.strip()
                    if cleaned:
                        data = json.loads(cleaned)
                        return self._validate_and_fix_data(data)
                except json.JSONDecodeError:
                    continue

        # If no JSON found, try to clean the content and parse again
        cleaned_content = content.strip()

        # Remove common prefixes/suffixes that might interfere
        prefixes_to_remove = [
            "```json",
            "```",
            "json:",
            "JSON:",
            "Here is the JSON:",
            "Response:",
        ]
        suffixes_to_remove = ["```", "```\n"]

        for prefix in prefixes_to_remove:
            if cleaned_content.startswith(prefix):
                cleaned_content = cleaned_content[len(prefix) :].strip()

        for suffix in suffixes_to_remove:
            if cleaned_content.endswith(suffix):
                cleaned_content = cleaned_content[: -len(suffix)].strip()

        try:
            data = json.loads(cleaned_content)
            return self._validate_and_fix_data(data)
        except json.JSONDecodeError:
            # If all fails, raise the original error with helpful info
            raise json.JSONDecodeError(
                f"Could not extract JSON from content. Original content (first 200 chars): {content[:200]!r}",
                content,
                0,
            )

    def _validate_and_fix_data(self, data: dict) -> dict:
        """Validate and fix common issues with parsed data."""
        # Ensure entities is a list
        if "entities" in data:
            if not isinstance(data["entities"], list):
                # Try to convert to list if it's a string
                if isinstance(data["entities"], str):
                    # Split by common delimiters
                    if "," in data["entities"]:
                        data["entities"] = [
                            e.strip() for e in data["entities"].split(",")
                        ]
                    elif ";" in data["entities"]:
                        data["entities"] = [
                            e.strip() for e in data["entities"].split(";")
                        ]
                    else:
                        # Single entity
                        data["entities"] = (
                            [data["entities"].strip()]
                            if data["entities"].strip()
                            else []
                        )
                else:
                    # Invalid type, default to empty list
                    data["entities"] = []
        else:
            data["entities"] = []

        # Ensure expanded_queries is a list
        if "expanded_queries" in data:
            if not isinstance(data["expanded_queries"], list):
                if isinstance(data["expanded_queries"], str):
                    data["expanded_queries"] = [data["expanded_queries"]]
                else:
                    data["expanded_queries"] = []
        else:
            data["expanded_queries"] = []

        # Ensure required fields have defaults
        if "query_type" not in data:
            data["query_type"] = "factual"
        if "semantic_intent" not in data:
            data["semantic_intent"] = ""
        if "time_filter" not in data:
            data["time_filter"] = None

        return data

    def analyze_with_all_features(
        self, query: str, document_summaries: Optional[List[str]] = None
    ) -> QueryIntent:
        """
        Analyze the query using all enabled features.

        This method integrates intent analysis, decomposition, step-back,
        and clarification question generation into a single call.

        Args:
            query: The user's query.
            document_summaries: Optional list of document summaries for context.

        Returns:
            A QueryIntent object populated with all analysis results.
        """
        try:
            logger.info("-- STEP 1: analyze_with_all_features --")
            # 1. Basic Intent Analysis (Type, Entities, Semantic Intent, Expansion)
            basic_intent = self.analyze(query)

            # 2. Decomposed Questions
            decomposed = []
            if self.config.enable_decomposition and basic_intent.expanded_queries:
                decomposed = self._decompose_query(query, basic_intent.expanded_queries)

            # 3. Step-Back Questions
            step_back = []
            if self.config.enable_step_back:
                step_back = self._generate_step_back_questions(query)

            logger.info("before generate clarifying questions")

            # 4. Clarifying Questions
            clarifying = self._generate_clarifying_questions(
                query, document_summaries=document_summaries
            )

            logger.info("after generate clarifying questions")

            # 5. Combine results
            basic_intent.decomposed_questions = decomposed
            basic_intent.step_back_questions = step_back
            basic_intent.clarifying_questions = clarifying

            return basic_intent

        except Exception as e:
            logger.error(f"Error in full analysis for query '{query}': {e}")
            # Return a default intent on error
            return QueryIntent(
                query_type="error",
                semantic_intent=query,
                entities=[],
                time_filter=None,
                expanded_queries=[],
                decomposed_questions=[],
                step_back_questions=[],
                clarifying_questions=[],
            )

    def _build_full_analysis_prompt(
        self,
        conversation: list[dict],
        user_query: str,
        relevance_check: Optional[bool] = None,
        document_summaries: Optional[list[str]] = None,
    ) -> str:
        """
        Builds the full system prompt for a multi-turn analysis task.
        """
        prompt_parts = []

        # Add conversation history to the prompt
        history_str = self._format_conversation_history(conversation)
        if history_str:
            prompt_parts.append(history_str)

        # Add document summaries to the prompt if available
        summaries_str = ""
        if document_summaries:
            summaries_list = "\n".join(f"- {s}" for s in document_summaries)
            summaries_str = f"""
<AvailableDocuments>
Here is a list of available technical manuals:
{summaries_list}
</AvailableDocuments>
"""

        # Add context from available documents
        if document_summaries:
            summaries_text = "\n".join([f"- {s}" for s in document_summaries])
            prompt_parts.append(
                f"CONTEXT: You have access to the following documents. Use this knowledge to improve your analysis and ask better clarifying questions if needed:\n{summaries_text}"
            )

        # Add relevance check information if provided
        if relevance_check is not None:
            prompt_parts.append(f"RELEVANCE_CHECK: {relevance_check}")

        # Instruction for the LLM
        # This is a heavily modified prompt that guides the LLM to perform all tasks
        # in a structured JSON output. It includes instructions for relevance checking,
        # clarification, and task/action/target extraction.
        return f"""
{history_str}
User Query: "{user_query}"
{summaries_str}
You are a sophisticated AI assistant responsible for analyzing user queries about technical manuals.
Your goal is to understand the user's intent and determine the next step. You must perform three tasks in order:
1.  **Relevance Check**: First, determine if the user's query is relevant to the available technical documents. The query is relevant if it asks for information contained in technical or repair manuals (e.g., "how to fix my engine," "torque specs," "show me a diagram"). The query is irrelevant if it's a general conversation, a greeting, or completely off-topic (e.g., "hello," "what's the weather," "tell me a joke").
2.  **Clarification**: If the query is relevant but too vague or ambiguous, you MUST ask clarifying questions. A query is vague if it lacks specific details needed to find the right information in the manuals.
    - **IMPORTANT**: If you have a list of available documents, use it to ask specific, multiple-choice questions. For example, if the user asks "how do I fix my engine?", and you have manuals for a "Caterpillar C18" and a "Subaru," ask "Which engine are you working on? A) Caterpillar C18, B) Subaru".
    - If no document list is available, ask open-ended questions to get the necessary details (e.g., "What is the make and model of the vehicle?").
    - If the query is specific enough, provide an empty list for `clarifying_questions`.
3.  **Task Identification**: If and only if the query is both relevant and specific enough (i.e., no clarification needed), identify the user's intended `task`, `action`, and `target`.
    - `task`: The overall goal (e.g., `search`, `lookup`, `find`).
    - `action`: The specific operation (e.g., `specifications`, `instructions`, `diagram`).
    - `target`: The main subject of the query (e.g., `timing belt`, `spark plugs`, `C18 engine`).

You MUST provide your response in a single, valid JSON object with the following structure and nothing else. Do not add any text before or after the JSON.
{{
  "is_relevant": <true_or_false>,
  "clarifying_questions": [
    {{
      "question": "Your first clarifying question?",
      "options": ["Option A", "Option B"]
    }},
    {{
      "question": "Your second question?",
      "options": []
    }}
  ],
  "task_action_target": {{
    "task": "<task>",
    "action": "<action>",
    "target": "<target>"
  }}
}}

Analyze the user query now.
"""

    def _format_conversation_history(self, conversation: list[dict]) -> str:
        """Formats conversation history for the prompt."""
        history_str = ""
        for turn in conversation:
            if "user" in turn:
                history_str += f"User: {turn['user']}\n"
            if "assistant" in turn:
                history_str += f"Assistant: {turn['assistant']}\n"
        return history_str
