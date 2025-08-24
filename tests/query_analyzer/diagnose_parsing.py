"""Diagnose why the main parsing chain is failing."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

def diagnose_parsing():
    """Diagnose the parsing issue."""
    print("🔍 Diagnosing Parsing Issues")
    print("=" * 50)
    
    # Recreate the pydantic model
    class QueryIntentModel(BaseModel):
        query_type: Literal["factual", "comparison", "aggregation", "explanation"] = Field(
            description="The type of query being asked"
        )
        entities: List[str] = Field(
            default_factory=list,
            description="Key entities mentioned in the query"
        )
        time_filter: Optional[str] = Field(
            default=None,
            description="Any time-based constraints in the query"
        )
        semantic_intent: str = Field(
            description="The core intent of what the user is trying to find"
        )
        expanded_queries: List[str] = Field(
            default_factory=list,
            description="Alternative phrasings or expanded versions of the query"
        )
    
    # Create parser
    parser = PydanticOutputParser(pydantic_object=QueryIntentModel)
    
    # Show format instructions
    print("📝 Format Instructions sent to LLM:")
    print("─" * 30)
    format_instructions = parser.get_format_instructions()
    print(format_instructions)
    print("─" * 30)
    
    # Create LLM
    llm = ChatOllama(model="llama3.2", temperature=0.0)
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a query analysis expert. Analyze the user's query and extract:
1. The type of query (factual, comparison, aggregation, or explanation)
2. Key entities mentioned
3. Any time-based constraints
4. The semantic intent - what the user really wants to know
5. Expanded queries - alternative ways to phrase the query for better retrieval

IMPORTANT: Return ONLY valid JSON data, not a schema or explanation.
Do not wrap the JSON in markdown code blocks (```).
Do not include any text before or after the JSON.
Your response must be pure JSON that can be parsed directly.

{format_instructions}"""),
        ("human", "{query}")
    ])
    
    # Test query
    test_query = "How does a jet engine compressor work?"
    
    print(f"\n🧪 Test Query: '{test_query}'")
    print("\n" + "─" * 50)
    
    # Get raw response
    messages = prompt.format_messages(
        query=test_query,
        format_instructions=format_instructions
    )
    
    print("📨 Full Prompt Sent to LLM:")
    print("─" * 30)
    for msg in messages:
        print(f"{msg.type}: {msg.content[:200]}...")
    print("─" * 30)
    
    raw_response = llm.invoke(messages)
    content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
    
    print("\n🤖 Raw LLM Response:")
    print("─" * 30)
    print(repr(content[:500]))
    print("─" * 30)
    
    # Try parsing
    print("\n🔬 Parsing Attempts:")
    
    # Direct parse attempt
    try:
        result = parser.parse(content)
        print("✅ Direct parsing successful!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Direct parsing failed: {e}")
        
        # Try JSON extraction
        try:
            # Remove markdown if present
            if content.startswith("```"):
                lines = content.split('\n')
                json_start = next((i for i, line in enumerate(lines) if line.strip() == "```json" or line.strip() == "```"), 0)
                json_end = next((i for i in range(len(lines)-1, json_start, -1) if lines[i].strip() == "```"), len(lines))
                content = '\n'.join(lines[json_start+1:json_end])
            
            data = json.loads(content)
            print("✅ JSON extraction successful!")
            print(f"Data: {data}")
            
            # Try creating model
            model = QueryIntentModel(**data)
            print("✅ Model creation successful!")
            print(f"Model: {model}")
        except Exception as e2:
            print(f"❌ JSON extraction failed: {e2}")

if __name__ == "__main__":
    diagnose_parsing()