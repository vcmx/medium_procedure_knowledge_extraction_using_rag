"""Quick test of LLM-based task-action-target evaluation."""

from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import RelevanceConfig

def quick_test():
    try:
        from langchain_ollama import ChatOllama
        
        llm = ChatOllama(model="llama3.2", temperature=0.0)
        config = RelevanceConfig(evaluation_mode="task_action_target")
        checker = ContextualRelevanceChecker(config, llm_provider=llm)
        
        query = "remove the oil filter"
        result = checker.check_relevance(query)
        
        print(f"Query: {query}")
        print(f"Relevant: {result.is_relevant}")
        print(f"Confidence: {result.confidence}")
        print(f"Domain matches: {result.domain_matches}")
        print(f"Explanation: {result.explanation}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    quick_test()