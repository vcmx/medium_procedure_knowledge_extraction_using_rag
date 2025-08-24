#!/usr/bin/env python3
"""
Simple interactive demonstration focusing on the clarification step.

This script demonstrates:
- How ambiguous queries trigger clarification
- Interactive question-answering
- Query rephrasing with context
- The impact of clarification on analysis quality

Run with: python tests/query_analyzer/interactive_clarification_demo.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from colorama import init, Fore, Style

from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.models import QueryAnalyzerConfig

# Initialize colorama
init(autoreset=True)


def interactive_clarification_demo():
    """Run an interactive clarification demonstration."""
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{'Interactive Clarification Demo':^60}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # Configure analyzer with clarification enabled
    config = QueryAnalyzerConfig(
        enable_clarification=True,
        enable_query_expansion=True,
        enable_decomposition=True,
        max_clarifying_questions=4
    )
    
    analyzer = OllamaQueryAnalyzer(config)
    
    # Example ambiguous queries
    example_queries = [
        "How do I fix it?",
        "Why is it slow?",
        "The system doesn't work",
        "What's wrong with the engine?",
        "How to improve performance?",
        "It's making a noise"
    ]
    
    print(f"{Fore.YELLOW}This demo shows how clarification improves query understanding.{Style.RESET_ALL}")
    print(f"\n{Fore.GREEN}Example ambiguous queries:{Style.RESET_ALL}")
    for i, q in enumerate(example_queries, 1):
        print(f"  {i}. {q}")
    
    print(f"\n{Fore.YELLOW}Commands:{Style.RESET_ALL}")
    print("  - Enter a number (1-6) to use an example query")
    print("  - Type your own ambiguous query")
    print("  - Type 'quit' to exit\n")
    
    while True:
        try:
            user_input = input(f"{Fore.GREEN}Enter query or number: {Style.RESET_ALL}").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit']:
                break
            
            # Check if user selected an example
            if user_input.isdigit() and 1 <= int(user_input) <= len(example_queries):
                query = example_queries[int(user_input) - 1]
                print(f"{Fore.CYAN}Selected: '{query}'{Style.RESET_ALL}")
            else:
                query = user_input
            
            print(f"\n{Fore.BLUE}{'='*50}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}Processing: '{query}'{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'='*50}{Style.RESET_ALL}\n")
            
            # First, analyze without clarification to show the difference
            print(f"{Fore.YELLOW}1️⃣  Analysis WITHOUT clarification:{Style.RESET_ALL}")
            intent_before = analyzer.analyze(query)
            print(f"   Intent: {intent_before.semantic_intent}")
            print(f"   Type: {intent_before.query_type}")
            if intent_before.entities:
                print(f"   Entities: {', '.join(intent_before.entities)}")
            
            # Now with interactive clarification
            print(f"\n{Fore.YELLOW}2️⃣  Analysis WITH clarification:{Style.RESET_ALL}")
            
            # Use analyze_with_clarification for automatic flow
            intent_after = analyzer.analyze_with_clarification(
                query,
                auto_clarify=True  # Automatically prompt for clarification
            )
            
            # Show the improvement
            print(f"\n{Fore.GREEN}📊 Results after clarification:{Style.RESET_ALL}")
            print(f"   Intent: {intent_after.semantic_intent}")
            print(f"   Type: {intent_after.query_type}")
            
            if intent_after.entities:
                print(f"   Entities: {', '.join(intent_after.entities)}")
            
            if hasattr(intent_after, 'clarified_query') and intent_after.clarified_query:
                print(f"\n{Fore.GREEN}✨ Clarified query:{Style.RESET_ALL}")
                print(f"   '{intent_after.clarified_query}'")
            
            # Show the difference in query expansions
            if intent_after.expanded_queries:
                print(f"\n{Fore.YELLOW}📝 Better query expansions:{Style.RESET_ALL}")
                for i, eq in enumerate(intent_after.expanded_queries[:3], 1):
                    print(f"   {i}. {eq}")
            
            print(f"\n{Fore.CYAN}{'─'*50}{Style.RESET_ALL}\n")
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Interrupted{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            continue
    
    print(f"\n{Fore.CYAN}Thank you for testing clarification!{Style.RESET_ALL}")


if __name__ == "__main__":
    interactive_clarification_demo()