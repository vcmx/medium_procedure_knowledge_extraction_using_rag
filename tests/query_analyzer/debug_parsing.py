"""Debug script to see what the LLM is actually returning."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.models import QueryAnalyzerConfig

def debug_llm_response():
    """Debug what the LLM is actually returning."""
    print("🔍 Debugging LLM Response Format")
    print("=" * 50)
    
    # Create analyzer
    config = QueryAnalyzerConfig(
        model_name="llama3.2",
        temperature=0.0,
        enable_query_expansion=True,
        enable_decomposition=False,
        enable_step_back=False,
        enable_clarification=False
    )
    
    analyzer = OllamaQueryAnalyzer(config)
    
    # Test query
    test_query = "How to optimize database performance?"
    
    print(f"Test Query: '{test_query}'")
    print("\n" + "─" * 50)
    
    # Show the prompt being sent
    try:
        prompt = analyzer._build_analysis_prompt(test_query)
        print("📋 Prompt being sent to LLM:")
        print("─" * 30)
        print(prompt)
        print("─" * 30)
    except Exception as e:
        print(f"Could not build prompt: {e}")
    
    print("\n" + "─" * 50)
    
    # Get raw LLM response
    try:
        from langchain_core.runnables import RunnablePassthrough
        
        raw_response = (
            {"query": RunnablePassthrough(), "format_instructions": lambda _: analyzer.parser.get_format_instructions()}
            | analyzer.prompt
            | analyzer.llm
        ).invoke(test_query)
        
        content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
        
        print("🤖 Raw LLM Response:")
        print("─" * 30)
        print(repr(content))  # Use repr to show exact characters
        print("─" * 30)
        print("Content:")
        print(content)
        print("─" * 30)
        
        # Try to parse as JSON
        print("\n🔬 JSON Parsing Attempts:")
        
        # Attempt 1: Direct parsing
        try:
            parsed = json.loads(content)
            print("✅ Direct JSON parsing successful!")
            print(f"Type: {type(parsed)}")
            print(f"Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dict'}")
            print(f"Content: {parsed}")
        except json.JSONDecodeError as e:
            print(f"❌ Direct JSON parsing failed: {e}")
            
            # Attempt 2: Use our new extraction method
            try:
                data = analyzer._extract_json_from_content(content)
                print("✅ New extraction method successful!")
                print(f"Type: {type(data)}")
                print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                print(f"Content: {data}")
            except Exception as e:
                print(f"❌ New extraction method failed: {e}")
                
                # Attempt 3: Check if it's a schema
                if "properties" in content and "required" in content:
                    print("🔧 Detected schema format, attempting extraction...")
                    try:
                        schema_dict = json.loads(content)
                        print(f"Schema keys: {list(schema_dict.keys())}")
                        
                        # Try to extract data
                        data = analyzer._extract_data_from_schema(schema_dict)
                        print(f"✅ Extracted data: {data}")
                    except Exception as e:
                        print(f"❌ Schema extraction failed: {e}")
                else:
                    print("❌ Not a schema format either")
                    
                    # Attempt 4: Look for JSON-like content
                    import re
                    json_pattern = r'\{.*\}'
                    matches = re.findall(json_pattern, content, re.DOTALL)
                    if matches:
                        print(f"🔍 Found {len(matches)} JSON-like patterns:")
                        for i, match in enumerate(matches):
                            print(f"  Pattern {i+1}: {match[:100]}...")
                            try:
                                parsed = json.loads(match)
                                print(f"  ✅ Pattern {i+1} is valid JSON!")
                                print(f"  Content: {parsed}")
                            except:
                                print(f"  ❌ Pattern {i+1} is not valid JSON")
        
        # Show the Pydantic format instructions
        print("\n📝 Expected Format Instructions:")
        print("─" * 30)
        format_instructions = analyzer.parser.get_format_instructions()
        print(format_instructions)
        print("─" * 30)
        
    except Exception as e:
        print(f"❌ Error getting raw response: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_llm_response()