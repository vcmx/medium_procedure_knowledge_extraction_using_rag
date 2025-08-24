"""Test the HyDE generator for errors."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.query_analyzer.hyde_generator import OllamaHyDEGenerator
from src.modules.query_analyzer.models import HyDEConfig

def test_hyde_generator():
    """Test HyDE document generation."""
    print("🧪 Testing HyDE Generator")
    print("=" * 50)
    
    # Create HyDE generator with default config
    config = HyDEConfig(
        model_name="llama3.2",
        temperature=0.7,
        max_length=300
    )
    
    hyde_generator = OllamaHyDEGenerator(config)
    
    # Test queries
    test_queries = [
        "How does a jet engine compressor work?",
        "What are the benefits of microservices architecture?",
        "Explain database indexing strategies",
        "How to debug memory leaks in Python?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: '{query}'")
        print("─" * 60)
        
        try:
            # Generate hypothetical document
            hyde_doc = hyde_generator.generate(query)
            
            print("✅ HyDE Document Generated:")
            print(f"Length: {len(hyde_doc)} chars")
            print("\n📄 Content:")
            print(hyde_doc)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("✅ HyDE testing complete!")

def test_hyde_config():
    """Test different HyDE configurations."""
    print("\n\n🔧 Testing HyDE Configurations")
    print("=" * 50)
    
    # Test with short length limit
    print("\n📏 Testing with short length limit (100 chars):")
    config = HyDEConfig(model_name="llama3.2", max_length=100)
    generator = OllamaHyDEGenerator(config)
    
    query = "Explain the theory of relativity"
    hyde_doc = generator.generate(query)
    print(f"Query: '{query}'")
    print(f"HyDE (truncated): {hyde_doc}")
    print(f"Length: {len(hyde_doc)} chars (limit: 100)")
    
    # Test with different temperature
    print("\n🌡️ Testing with high temperature (1.0):")
    config = HyDEConfig(model_name="llama3.2", temperature=1.0)
    generator = OllamaHyDEGenerator(config)
    
    hyde_doc = generator.generate(query)
    print(f"Query: '{query}'")
    print(f"HyDE (creative): {hyde_doc[:150]}...")

if __name__ == "__main__":
    try:
        test_hyde_generator()
        test_hyde_config()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()