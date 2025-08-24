#!/usr/bin/env python3
"""
Interactive demonstration of the 5-step conversational query processing flow.

This script allows real human interaction to test:
1. Initial prompt reception
2. Relevance checking with feedback
3. Interactive clarification
4. Intent analysis visualization  
5. Query enhancement display

Run with: python tests/query_analyzer/interactive_conversational_demo.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import logging
from typing import Optional, Dict, List
from datetime import datetime
from colorama import init, Fore, Back, Style

from src.modules.query_analyzer.conversational_workflow import ConversationalWorkflow
from src.modules.query_analyzer.conversation_state import UserLevel
from src.modules.query_analyzer.models import RelevanceConfig

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Configure logging to show workflow steps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class InteractiveConversationalDemo:
    """Interactive demonstration of conversational query analysis."""
    
    def __init__(self):
        """Initialize the demo with conversational workflow."""
        self.workflow = None
        self.session_id = f"interactive_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.query_count = 0
        
    def print_header(self, text: str):
        """Print a styled header."""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{text:^60}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    def print_step(self, step_num: int, step_name: str, status: str = ""):
        """Print a workflow step with formatting."""
        status_color = Fore.GREEN if "✅" in status else Fore.YELLOW if "⚠️" in status else Fore.RED if "❌" in status else Fore.WHITE
        print(f"\n{Fore.BLUE}Step {step_num}: {Fore.WHITE}{step_name} {status_color}{status}")
    
    def print_info(self, label: str, value: str):
        """Print labeled information."""
        print(f"{Fore.YELLOW}{label}:{Style.RESET_ALL} {value}")
    
    def setup_workflow(self):
        """Set up the conversational workflow with user preferences."""
        self.print_header("Conversational Query Analysis Setup")
        
        # Choose relevance mode
        print(f"\n{Fore.GREEN}Choose relevance checking mode:{Style.RESET_ALL}")
        print("1. Two-stage (vocabulary + semantic)")
        print("2. Task-action-target (LLM-based) - Default")
        print("3. Disabled")
        
        mode_choice = input(f"\n{Fore.CYAN}Enter choice (1-3) [{Fore.WHITE}2{Fore.CYAN}]: {Style.RESET_ALL}").strip() or "2"
        
        enable_relevance = mode_choice != "3"
        evaluation_mode = "task_action_target" if mode_choice == "2" else "two_stage"
        
        # Choose rejection mode
        rejection_mode = "hard"
        if enable_relevance:
            print(f"\n{Fore.GREEN}Choose rejection mode:{Style.RESET_ALL}")
            print("1. Hard (reject immediately)")
            print("2. Soft (continue with low confidence)")
            print("3. Score only (never reject)")
            
            reject_choice = input(f"\n{Fore.CYAN}Enter choice (1-3) [{Fore.WHITE}1{Fore.CYAN}]: {Style.RESET_ALL}").strip() or "1"
            rejection_mode = ["hard", "soft", "score"][int(reject_choice) - 1] if reject_choice in ["1", "2", "3"] else "hard"
        
        # Enable clarification?
        print(f"\n{Fore.GREEN}Enable interactive clarification?{Style.RESET_ALL}")
        enable_clarification = input(f"{Fore.CYAN}(y/n) [{Fore.WHITE}y{Fore.CYAN}]: {Style.RESET_ALL}").strip().lower() != 'n'
        
        # User expertise level
        print(f"\n{Fore.GREEN}Select user expertise level:{Style.RESET_ALL}")
        print("1. Novice")
        print("2. Experienced")
        print("3. Expert")
        
        level_choice = input(f"\n{Fore.CYAN}Enter choice (1-3) [{Fore.WHITE}1{Fore.CYAN}]: {Style.RESET_ALL}").strip() or "1"
        user_levels = [UserLevel.NOVICE, UserLevel.EXPERIENCED, UserLevel.EXPERT]
        user_level = user_levels[int(level_choice) - 1] if level_choice in ["1", "2", "3"] else UserLevel.NOVICE
        
        # Create workflow
        print(f"\n{Fore.GREEN}Creating workflow...{Style.RESET_ALL}")
        self.workflow = ConversationalWorkflow(
            analyzer_type="ollama",
            enable_relevance_check=enable_relevance,
            enable_clarification=enable_clarification
        )
        
        # Configure relevance if enabled
        if enable_relevance and self.workflow.relevance_checker:
            self.workflow.relevance_checker.config.evaluation_mode = evaluation_mode
            self.workflow.relevance_checker.config.rejection_mode = rejection_mode
        
        self.user_level = user_level
        
        print(f"\n{Fore.GREEN}✅ Workflow configured!{Style.RESET_ALL}")
        print(f"  - Relevance: {Fore.CYAN}{evaluation_mode if enable_relevance else 'disabled'}{Style.RESET_ALL}")
        print(f"  - Rejection: {Fore.CYAN}{rejection_mode if enable_relevance else 'n/a'}{Style.RESET_ALL}")
        print(f"  - Clarification: {Fore.CYAN}{'enabled' if enable_clarification else 'disabled'}{Style.RESET_ALL}")
        print(f"  - User level: {Fore.CYAN}{user_level}{Style.RESET_ALL}")
    
    def collect_clarification_responses(self, questions: List[str]) -> Dict[str, str]:
        """Interactively collect responses to clarification questions."""
        responses = {}
        
        print(f"\n{Fore.YELLOW}📋 Please answer these clarifying questions:{Style.RESET_ALL}")
        for i, question in enumerate(questions, 1):
            print(f"\n{Fore.CYAN}{i}. {question}{Style.RESET_ALL}")
            response = input(f"   {Fore.GREEN}Your answer: {Style.RESET_ALL}").strip()
            if response:
                responses[question] = response
        
        return responses
    
    def display_query_intent(self, intent):
        """Display the analyzed query intent."""
        print(f"\n{Fore.GREEN}📊 Query Analysis Results:{Style.RESET_ALL}")
        
        self.print_info("Query Type", intent.query_type)
        self.print_info("Semantic Intent", intent.semantic_intent)
        
        if intent.entities:
            self.print_info("Entities", ", ".join(intent.entities))
        
        if intent.expanded_queries:
            print(f"\n{Fore.YELLOW}Expanded Queries ({len(intent.expanded_queries)}):{Style.RESET_ALL}")
            for i, eq in enumerate(intent.expanded_queries[:3], 1):
                print(f"  {i}. {eq}")
            if len(intent.expanded_queries) > 3:
                print(f"  ... and {len(intent.expanded_queries) - 3} more")
        
        if intent.decomposed_questions:
            print(f"\n{Fore.YELLOW}Decomposed Questions ({len(intent.decomposed_questions)}):{Style.RESET_ALL}")
            for i, dq in enumerate(intent.decomposed_questions[:3], 1):
                print(f"  {i}. {dq}")
            if len(intent.decomposed_questions) > 3:
                print(f"  ... and {len(intent.decomposed_questions) - 3} more")
        
        if intent.step_back_questions:
            print(f"\n{Fore.YELLOW}Step-back Questions ({len(intent.step_back_questions)}):{Style.RESET_ALL}")
            for i, sq in enumerate(intent.step_back_questions, 1):
                print(f"  {i}. {sq}")
    
    def process_single_query(self, query: str):
        """Process a single query through the 5-step flow."""
        self.query_count += 1
        
        self.print_header(f"Query #{self.query_count}: {query[:50]}...")
        
        # Step 1: Initial prompt
        self.print_step(1, "Initial Prompt Reception", "✅")
        print(f"  Received: '{query}'")
        
        try:
            # First, process the query to check if clarification is needed
            initial_result, initial_metadata = self.workflow.process_user_query(
                query=query,
                session_id=self.session_id,
                user_level=self.user_level
            )
            
            # Check if we need to collect clarification interactively
            if (self.workflow.conversation_manager.enable_clarification and 
                initial_result.intent and 
                initial_result.intent.clarifying_questions and
                not initial_result.rejection_reason):
                
                # Show that we're entering clarification phase
                self.print_step(3, "Clarification", "🔄 Needed")
                
                # Get clarification questions
                clarification_questions = initial_result.intent.clarifying_questions[:3]  # Limit to 3
                
                # Collect responses interactively
                responses = self.collect_clarification_responses(clarification_questions)
                
                if responses:
                    # Re-process with clarification responses
                    result = self.workflow.conversation_manager.process_query(
                        query=query,
                        session_id=self.session_id,
                        user_responses=responses
                    )
                    
                    # Build proper metadata for display
                    metadata = initial_metadata.copy()
                    metadata["steps_completed"] = metadata.get("steps_completed", [])
                    if "clarification_performed" not in metadata["steps_completed"]:
                        metadata["steps_completed"].append("clarification_performed")
                    metadata["clarification_needed"] = True
                    metadata["clarification_questions"] = clarification_questions
                else:
                    # No responses provided, use initial result
                    result, metadata = initial_result, initial_metadata
                    self.print_info("Note", "No responses provided, continuing without clarification")
            else:
                # Use initial result if no clarification needed or rejected
                result, metadata = initial_result, initial_metadata
            
            # Display workflow steps
            steps_completed = metadata.get('steps_completed', [])
            
            # Step 2: Relevance check
            if 'relevance_check_passed' in steps_completed:
                self.print_step(2, "Relevance Check", "✅ Passed")
                print(f"  Confidence: {result.relevance_score:.2f}")
                if result.intent and result.intent.relevance_info:
                    print(f"  Stage: {result.intent.relevance_info.stage}")
                    print(f"  Explanation: {result.intent.relevance_info.explanation}")
            elif 'relevance_check_failed' in steps_completed:
                self.print_step(2, "Relevance Check", "❌ Failed")
                print(f"  Reason: {result.rejection_reason}")
                if result.intent and result.intent.relevance_info and result.intent.relevance_info.suggestions:
                    print(f"\n{Fore.YELLOW}💡 Suggestions:{Style.RESET_ALL}")
                    for suggestion in result.intent.relevance_info.suggestions:
                        print(f"  - {suggestion}")
                return  # Exit early if rejected
            else:
                self.print_step(2, "Relevance Check", "⚠️ Skipped")
            
            # Step 3: Clarification
            if 'clarification_performed' in steps_completed:
                self.print_step(3, "Clarification", "✅ Performed")
                if result.clarifications:
                    print(f"\n{Fore.YELLOW}Clarifications made:{Style.RESET_ALL}")
                    for clarification in result.clarifications:
                        print(f"  Q: {clarification.question}")
                        print(f"  A: {clarification.answer}")
                    
                    # Show query synthesis step
                    if result.final_query != query:
                        print(f"\n{Fore.CYAN}🔄 Query Synthesis:{Style.RESET_ALL}")
                        print(f"  Original: '{query}'")
                        print(f"  Synthesized: '{result.final_query}'")
            elif result.intent and result.intent.clarifying_questions and not result.rejection_reason:
                # Clarification was needed but not performed (user didn't provide responses)
                self.print_step(3, "Clarification", "⚠️ Needed but skipped")
                print(f"  Questions were: {len(result.intent.clarifying_questions)}")
            elif 'clarification_skipped' in steps_completed:
                self.print_step(3, "Clarification", "➖ Not needed")
            
            # Step 4: Intent Analysis
            if 'intent_analysis_completed' in steps_completed and result.intent:
                self.print_step(4, "Intent Analysis", "✅ Completed")
                self.display_query_intent(result.intent)
            else:
                self.print_step(4, "Intent Analysis", "⚠️ Limited")
            
            # Step 5: Query Enhancement
            if 'query_enhancement_completed' in steps_completed:
                self.print_step(5, "Query Enhancement", "✅ Completed")
                enhancements = []
                if result.intent:
                    if result.intent.expanded_queries:
                        enhancements.append(f"{len(result.intent.expanded_queries)} expansions")
                    if result.intent.decomposed_questions:
                        enhancements.append(f"{len(result.intent.decomposed_questions)} decompositions")
                    if result.intent.step_back_questions:
                        enhancements.append(f"{len(result.intent.step_back_questions)} step-backs")
                print(f"  Generated: {', '.join(enhancements)}")
            else:
                self.print_step(5, "Query Enhancement", "➖ Not performed")
            
            # Show final query if clarified
            if result.final_query != query:
                print(f"\n{Fore.GREEN}📝 Final Query:{Style.RESET_ALL}")
                print(f"  '{result.final_query}'")
            
        except Exception as e:
            print(f"\n{Fore.RED}❌ Error processing query: {str(e)}{Style.RESET_ALL}")
    
    def show_session_summary(self):
        """Display the conversation session summary."""
        try:
            summary = self.workflow.get_session_summary(self.session_id)
            
            self.print_header("Session Summary")
            
            print(f"{Fore.YELLOW}Total queries:{Style.RESET_ALL} {summary.get('total_queries', 0)}")
            print(f"{Fore.YELLOW}User level:{Style.RESET_ALL} {summary.get('user_level', 'unknown')}")
            
            if summary.get('entities_mentioned'):
                print(f"\n{Fore.YELLOW}Entities discussed:{Style.RESET_ALL}")
                for entity in summary['entities_mentioned']:
                    print(f"  - {entity}")
            
            if summary.get('topics_discussed'):
                print(f"\n{Fore.YELLOW}Topics covered:{Style.RESET_ALL}")
                for topic in summary['topics_discussed']:
                    print(f"  - {topic}")
            
            if summary.get('clarifications_made'):
                print(f"\n{Fore.YELLOW}Clarifications:{Style.RESET_ALL} {len(summary['clarifications_made'])}")
            
        except Exception as e:
            print(f"{Fore.RED}Could not retrieve session summary: {str(e)}{Style.RESET_ALL}")
    
    def run(self):
        """Run the interactive demonstration."""
        self.print_header("Interactive Conversational Query Analysis")
        print(f"\n{Fore.CYAN}This demo allows you to test the 5-step conversational flow:")
        print("1. Initial prompt reception")
        print("2. Relevance checking")
        print("3. Interactive clarification")
        print("4. Intent analysis")
        print("5. Query enhancement")
        
        # Set up workflow
        self.setup_workflow()
        
        # Main interaction loop
        print(f"\n{Fore.GREEN}Ready to process queries!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Commands:{Style.RESET_ALL}")
        print("  - Type your query and press Enter")
        print("  - Type 'summary' to see session summary")
        print("  - Type 'reset' to start a new session")
        print("  - Type 'quit' or 'exit' to end\n")
        
        while True:
            try:
                query = input(f"{Fore.GREEN}Enter query: {Style.RESET_ALL}").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit']:
                    break
                
                if query.lower() == 'summary':
                    self.show_session_summary()
                    continue
                
                if query.lower() == 'reset':
                    self.session_id = f"interactive_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.query_count = 0
                    print(f"{Fore.CYAN}🔄 Resetting workflow configuration...{Style.RESET_ALL}")
                    self.setup_workflow()
                    
                    # Show ready message again after reset
                    print(f"\n{Fore.GREEN}Ready to process queries!{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Commands:{Style.RESET_ALL}")
                    print("  - Type your query and press Enter")
                    print("  - Type 'summary' to see session summary")
                    print("  - Type 'reset' to start a new session")
                    print("  - Type 'quit' or 'exit' to end\n")
                    continue
                
                # Process the query
                self.process_single_query(query)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        
        # Final summary
        print(f"\n{Fore.CYAN}Thank you for testing!{Style.RESET_ALL}")
        self.show_session_summary()
        
        # Clean up
        if self.workflow:
            self.workflow.clear_session(self.session_id)


def main():
    """Run the interactive demonstration."""
    demo = InteractiveConversationalDemo()
    demo.run()


if __name__ == "__main__":
    main()