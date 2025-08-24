#!/usr/bin/env python3
"""
Interactive demo for the multi-agent system.

Allows users to interact with the agent system in real-time,
submit queries, provide clarification responses, and explore features.
"""

import sys
import os
import json
from typing import Dict, Any, Optional
from colorama import Fore, Style, init
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.modules.agent import AgentController
import logging

# Initialize colorama
init(autoreset=True)

# Configure logging to be less verbose for interactive demo
logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')


class InteractiveAgentDemo:
    """Interactive demo for the agent system."""
    
    def __init__(self):
        """Initialize the interactive demo."""
        self.controller = None
        self.current_session = None
        self.sessions = {}
        
    def print_header(self):
        """Print welcome header."""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'🤖 Multi-Agent System Interactive Demo'.center(80)}")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.WHITE}Featuring: Supervisor + Query Analyzer + RAG/MCP Agents")
        print(f"{Fore.YELLOW}Type 'help' for available commands or 'quit' to exit")
        print(f"{Fore.CYAN}{'='*80}\n")
    
    def print_help(self):
        """Print help information."""
        print(f"\n{Fore.GREEN}Available Commands:")
        print(f"{Fore.WHITE}  query <text>     - Submit a query to the agent system")
        print(f"{Fore.WHITE}  session new      - Create a new session")
        print(f"{Fore.WHITE}  session list     - List all sessions")
        print(f"{Fore.WHITE}  session switch   - Switch to a different session")
        print(f"{Fore.WHITE}  session clear    - Clear current session")
        print(f"{Fore.WHITE}  status           - Show agent system status")
        print(f"{Fore.WHITE}  demo             - Run example queries")
        if hasattr(self, 'search_enabled') and self.search_enabled:
            print(f"{Fore.WHITE}  search <query>   - Run direct web search")
        print(f"{Fore.WHITE}  help             - Show this help message")
        print(f"{Fore.WHITE}  quit/exit        - Exit the demo\n")
    
    def initialize_controller(self):
        """Initialize the agent controller."""
        print(f"{Fore.YELLOW}Initializing agent system...")
        
        # Get configuration
        print(f"\n{Fore.CYAN}Configuration:")
        enable_rag = input(f"{Fore.WHITE}Enable RAG agent? (y/n) [{Fore.GREEN}y{Fore.WHITE}]: ").strip().lower() != 'n'
        enable_mcp = input(f"{Fore.WHITE}Enable MCP agent? (y/n) [{Fore.GREEN}y{Fore.WHITE}]: ").strip().lower() != 'n'
        
        # Check for search agent
        enable_search = False
        if os.getenv("TAVILY_API_KEY"):
            enable_search = input(f"{Fore.WHITE}Enable Search agent? (y/n) [{Fore.GREEN}y{Fore.WHITE}]: ").strip().lower() != 'n'
            if enable_search:
                print(f"{Fore.GREEN}✅ Tavily API key found. Search agent will be enabled.")
        else:
            print(f"{Fore.YELLOW}⚠️  TAVILY_API_KEY not found. Search agent disabled.")
            print(f"{Fore.WHITE}   To enable search: export TAVILY_API_KEY='your-key'")
        
        self.controller = AgentController(
            llm_model="llama3.2",
            enable_rag=enable_rag,
            enable_mcp=enable_mcp,
            enable_search=enable_search
        )
        
        self.search_enabled = enable_search
        
        available_agents = self.controller.available_agents
        print(f"{Fore.GREEN}✅ Agent system initialized!")
        print(f"{Fore.WHITE}   Available agents: {', '.join(available_agents)}")
        
        # Create initial session
        self.create_session()
    
    def create_session(self):
        """Create a new session."""
        print(f"\n{Fore.CYAN}Creating new session...")
        
        # Get user level
        print(f"{Fore.WHITE}Select user expertise level:")
        print(f"  1. {Fore.GREEN}NOVICE{Fore.WHITE} - Detailed explanations")
        print(f"  2. {Fore.YELLOW}EXPERIENCED{Fore.WHITE} - Balanced detail")
        print(f"  3. {Fore.RED}EXPERT{Fore.WHITE} - Concise responses")
        
        choice = input(f"\n{Fore.WHITE}Enter choice (1-3) [{Fore.YELLOW}2{Fore.WHITE}]: ").strip() or "2"
        
        level_map = {"1": "NOVICE", "2": "EXPERIENCED", "3": "EXPERT"}
        user_level = level_map.get(choice, "EXPERIENCED")
        
        session_id = self.controller.create_session(user_level)
        self.current_session = session_id
        self.sessions[session_id] = {"level": user_level, "queries": 0}
        
        print(f"{Fore.GREEN}✅ Session created: {session_id} ({user_level})")
    
    def process_query(self, query: str):
        """Process a user query."""
        if not self.current_session:
            print(f"{Fore.RED}❌ No active session. Create one with 'session new'")
            return
        
        print(f"\n{Fore.CYAN}Processing query: {Fore.WHITE}{query}")
        print(f"{Fore.YELLOW}{'─'*80}")
        
        # Track query count
        self.sessions[self.current_session]["queries"] += 1
        
        # Process query
        clarification_questions = []
        enhanced_query = None
        
        try:
            for step in self.controller.process_query(query, self.current_session):
                agent_name = step["agent"]
                output = step["output"]
                
                if agent_name == "system":
                    if output["type"] == "final_result":
                        print(f"\n{Fore.GREEN}✅ Processing complete!")
                        break
                    elif output["type"] == "error":
                        print(f"\n{Fore.RED}❌ Error: {output['error']}")
                        break
                else:
                    self._print_agent_output(agent_name, output)
                    
                    # Check for clarification
                    if output.get("clarification_needed"):
                        clarification_questions = output.get("clarification_questions", [])
                        if clarification_questions:
                            print(f"\n{Fore.YELLOW}🤔 The agent needs clarification:")
                            for i, q in enumerate(clarification_questions, 1):
                                print(f"{Fore.WHITE}   {i}. {q}")
                            
                            # Check for step-back questions and offer search
                            analysis_results = output.get("analysis_results", {})
                            intent_info = analysis_results.get("intent", {})
                            step_back_questions = intent_info.get("step_back_questions", [])
                            
                            if step_back_questions and hasattr(self, 'search_enabled') and self.search_enabled:
                                self._offer_search_for_step_back(step_back_questions)
                            
                            break
                    
                    # Check for step-back questions even when no clarification needed
                    if agent_name == "query_analyzer" and not output.get("clarification_needed"):
                        analysis_results = output.get("analysis_results", {})
                        intent_info = analysis_results.get("intent", {})
                        step_back_questions = intent_info.get("step_back_questions", [])
                        
                        # Debug: Show if step-back questions were generated
                        if step_back_questions:
                            print(f"{Fore.BLUE}🔍 Generated {len(step_back_questions)} step-back questions")
                        
                        if step_back_questions and hasattr(self, 'search_enabled') and self.search_enabled:
                            self._offer_search_for_step_back(step_back_questions)
                    
                    # Track enhanced query
                    if output.get("enhanced_query"):
                        enhanced_query = output["enhanced_query"]
        
        except Exception as e:
            print(f"\n{Fore.RED}❌ Error processing query: {e}")
            return
        
        # Handle clarification if needed
        if clarification_questions:
            self._handle_clarification(query, clarification_questions)
        elif enhanced_query and enhanced_query != query:
            print(f"\n{Fore.GREEN}📝 Enhanced query: {Fore.WHITE}{enhanced_query}")
    
    def _handle_clarification(self, original_query: str, questions: list):
        """Handle clarification workflow."""
        print(f"\n{Fore.CYAN}Please provide clarification responses:")
        print(f"{Fore.YELLOW}(Press Enter to skip a question)")
        
        responses = {}
        for i, question in enumerate(questions, 1):
            answer = input(f"\n{Fore.WHITE}Q{i}: {question}\n{Fore.GREEN}A{i}: ").strip()
            if answer:
                responses[question] = answer
        
        if not responses:
            print(f"{Fore.YELLOW}No responses provided. Query processing stopped.")
            return
        
        print(f"\n{Fore.CYAN}Processing with clarification responses...")
        print(f"{Fore.YELLOW}{'─'*80}")
        
        # Process with clarification
        try:
            for step in self.controller.process_query(
                original_query, 
                self.current_session,
                clarification_responses=responses
            ):
                agent_name = step["agent"]
                output = step["output"]
                
                if agent_name == "system":
                    if output["type"] == "final_result":
                        print(f"\n{Fore.GREEN}✅ Clarification processing complete!")
                        break
                else:
                    self._print_agent_output(agent_name, output)
                    
                    # Show enhanced query if available
                    if output.get("enhanced_query"):
                        print(f"\n{Fore.GREEN}📝 Enhanced query: {Fore.WHITE}{output['enhanced_query']}")
        
        except Exception as e:
            print(f"\n{Fore.RED}❌ Error in clarification: {e}")
    
    def _print_agent_output(self, agent_name: str, output: Dict[str, Any]):
        """Print agent output in a formatted way."""
        agent_colors = {
            "supervisor": Fore.CYAN,
            "query_analyzer": Fore.GREEN,
            "rag": Fore.YELLOW,
            "mcp": Fore.MAGENTA,
            "search": Fore.BLUE
        }
        
        color = agent_colors.get(agent_name, Fore.WHITE)
        print(f"\n{color}🤖 {agent_name.upper()} AGENT:")
        
        # Show workflow stage
        if "workflow_stage" in output:
            print(f"{Fore.WHITE}   📊 Stage: {output['workflow_stage']}")
        
        # Show messages
        if "messages" in output:
            for message in output["messages"]:
                content = message.content if hasattr(message, 'content') else str(message)
                # Limit output length for readability
                if len(content) > 500:
                    content = content[:500] + "..."
                print(f"{Fore.WHITE}   {content}")
        
        # Show analysis results summary
        if output.get("analysis_results"):
            results = output["analysis_results"]
            if "intent" in results:
                intent = results["intent"]
                print(f"{Fore.WHITE}   📋 Query type: {intent.get('query_type', 'unknown')}")
                print(f"{Fore.WHITE}   🎯 Intent: {intent.get('semantic_intent', 'unknown')}")
            
            # Show search results if available
            if "search_results" in results:
                search_info = results["search_results"]
                print(f"{Fore.WHITE}   🔍 Search results: {search_info.get('num_results', 0)} found")
                if search_info.get('search_query'):
                    print(f"{Fore.WHITE}   🔎 Search query: {search_info['search_query']}")
    
    def show_status(self):
        """Show agent system status."""
        if not self.controller:
            print(f"{Fore.RED}❌ Agent system not initialized")
            return
        
        status = self.controller.get_agent_status()
        
        print(f"\n{Fore.CYAN}Agent System Status:")
        print(f"{Fore.YELLOW}{'─'*40}")
        
        # Supervisor status
        supervisor = status.get("supervisor", {})
        print(f"{Fore.WHITE}Supervisor:")
        print(f"  - Model: {supervisor.get('llm_model', 'unknown')}")
        print(f"  - Available agents: {', '.join(supervisor.get('available_agents', []))}")
        
        # Query Analyzer status
        qa = status.get("query_analyzer", {})
        print(f"\n{Fore.WHITE}Query Analyzer:")
        print(f"  - Active sessions: {qa.get('active_sessions', 0)}")
        print(f"  - Analyzer type: {qa.get('analyzer_type', 'unknown')}")
        
        # RAG status
        rag = status.get("rag_agent", {})
        print(f"\n{Fore.WHITE}RAG Agent:")
        print(f"  - Enabled: {rag.get('enabled', False)}")
        print(f"  - Status: {rag.get('status', 'unknown')}")
        
        # MCP status
        mcp = status.get("mcp_agent", {})
        print(f"\n{Fore.WHITE}MCP Agent:")
        print(f"  - Enabled: {mcp.get('enabled', False)}")
        print(f"  - Available tools: {mcp.get('available_tools', 0)}")
        print(f"  - Status: {mcp.get('status', 'unknown')}")
        
        # Search status
        search = status.get("search_agent", {})
        print(f"\n{Fore.WHITE}Search Agent:")
        print(f"  - Enabled: {search.get('enabled', False)}")
        print(f"  - API Key: {'✅ Set' if os.getenv('TAVILY_API_KEY') else '❌ Missing'}")
        print(f"  - Status: {search.get('status', 'unknown')}")
    
    def run_demo_queries(self):
        """Run demonstration queries."""
        print(f"\n{Fore.CYAN}Running demonstration queries...")
        
        demo_queries = [
            ("Simple technical query", "How do I check engine oil level?"),
            ("Vague query (triggers clarification)", "How do I fix this?"),
            ("Complex query (multi-agent)", "What are the torque specs for cylinder head bolts on a 2019 Honda Civic?"),
            ("Procedural query", "Explain the steps to replace brake pads"),
        ]
        
        # Add search queries if search is enabled
        if hasattr(self, 'search_enabled') and self.search_enabled:
            demo_queries.extend([
                ("Current events query (uses search)", "What are the latest developments in AI?"),
                ("Real-time information", "What's the current price of Tesla stock?"),
                ("Recent news query", "What happened in technology news this week?"),
            ])
        
        for title, query in demo_queries:
            print(f"\n{Fore.YELLOW}Demo: {title}")
            response = input(f"{Fore.WHITE}Run this demo? (y/n) [{Fore.GREEN}y{Fore.WHITE}]: ").strip().lower()
            
            if response != 'n':
                self.process_query(query)
                input(f"\n{Fore.YELLOW}Press Enter to continue...")
    
    def list_sessions(self):
        """List all sessions."""
        sessions = self.controller.list_sessions()
        
        print(f"\n{Fore.CYAN}Active Sessions:")
        print(f"{Fore.YELLOW}{'─'*60}")
        
        for session in sessions:
            sid = session['session_id']
            current = " (current)" if sid == self.current_session else ""
            local_info = self.sessions.get(sid, {})
            
            print(f"{Fore.WHITE}  {sid}{Fore.GREEN}{current}")
            print(f"{Fore.WHITE}    - Level: {session['user_level']}")
            print(f"{Fore.WHITE}    - Messages: {session['message_count']}")
            print(f"{Fore.WHITE}    - Queries: {local_info.get('queries', 0)}")
    
    def switch_session(self):
        """Switch to a different session."""
        sessions = self.controller.list_sessions()
        
        if len(sessions) <= 1:
            print(f"{Fore.YELLOW}Only one session available")
            return
        
        self.list_sessions()
        
        print(f"\n{Fore.CYAN}Enter session ID to switch to:")
        session_id = input(f"{Fore.WHITE}Session ID: ").strip()
        
        if any(s['session_id'] == session_id for s in sessions):
            self.current_session = session_id
            print(f"{Fore.GREEN}✅ Switched to session: {session_id}")
        else:
            print(f"{Fore.RED}❌ Invalid session ID")
    
    def clear_session(self):
        """Clear current session."""
        if not self.current_session:
            print(f"{Fore.RED}❌ No active session")
            return
        
        confirm = input(f"{Fore.YELLOW}Clear current session? (y/n): ").strip().lower()
        
        if confirm == 'y':
            self.controller.clear_session(self.current_session)
            if self.current_session in self.sessions:
                del self.sessions[self.current_session]
            
            print(f"{Fore.GREEN}✅ Session cleared")
            
            # Create new session if no sessions left
            if not self.controller.list_sessions():
                self.create_session()
            else:
                # Switch to first available session
                sessions = self.controller.list_sessions()
                self.current_session = sessions[0]['session_id']
                print(f"{Fore.YELLOW}Switched to session: {self.current_session}")
    
    def run(self):
        """Run the interactive demo."""
        self.print_header()
        self.initialize_controller()
        
        while True:
            try:
                # Show prompt
                session_info = f" [{self.current_session[:8]}...]" if self.current_session else ""
                command = input(f"\n{Fore.CYAN}agent-demo{session_info}> {Fore.WHITE}").strip()
                
                if not command:
                    continue
                
                # Parse command
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                # Handle commands
                if cmd in ['quit', 'exit']:
                    print(f"{Fore.YELLOW}Goodbye! 👋")
                    break
                
                elif cmd == 'help':
                    self.print_help()
                
                elif cmd == 'query' and args:
                    self.process_query(args)
                
                elif cmd == 'session':
                    if args == 'new':
                        self.create_session()
                    elif args == 'list':
                        self.list_sessions()
                    elif args == 'switch':
                        self.switch_session()
                    elif args == 'clear':
                        self.clear_session()
                    else:
                        print(f"{Fore.RED}Unknown session command. Use: new, list, switch, or clear")
                
                elif cmd == 'status':
                    self.show_status()
                
                elif cmd == 'demo':
                    self.run_demo_queries()
                
                elif cmd == 'search' and args:
                    if hasattr(self, 'search_enabled') and self.search_enabled:
                        self._run_direct_search(args)
                    else:
                        print(f"{Fore.RED}Search agent not enabled. Set TAVILY_API_KEY to enable search.")
                
                elif cmd == 'query':
                    print(f"{Fore.RED}Please provide a query. Example: query How do I check oil?")
                
                else:
                    print(f"{Fore.RED}Unknown command: {cmd}")
                    print(f"{Fore.YELLOW}Type 'help' for available commands")
            
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Use 'quit' to exit")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}")
                logging.exception("Interactive demo error")
    
    def _offer_search_for_step_back(self, step_back_questions: list):
        """Offer to search for step-back questions."""
        print(f"\n{Fore.BLUE}🔍 The agent generated step-back questions that could benefit from web search:")
        for i, q in enumerate(step_back_questions[:3], 1):  # Show first 3
            print(f"{Fore.WHITE}   {i}. {q}")
        
        if len(step_back_questions) > 3:
            print(f"{Fore.WHITE}   ... and {len(step_back_questions) - 3} more")
        
        search_choice = input(f"\n{Fore.CYAN}Would you like to search the web for these questions? (y/n): ").strip().lower()
        
        if search_choice == 'y':
            print(f"\n{Fore.BLUE}🔍 Searching the web for step-back questions...")
            for i, question in enumerate(step_back_questions[:3], 1):
                print(f"\n{Fore.YELLOW}Searching for: {question}")
                self._run_direct_search(question, show_header=False)
                if i < len(step_back_questions[:3]):
                    input(f"{Fore.WHITE}Press Enter to search next question...")
    
    def _run_direct_search(self, query: str, show_header: bool = True):
        """Run a direct search query."""
        if show_header:
            print(f"\n{Fore.BLUE}🔍 Direct Search: {Fore.WHITE}{query}")
            print(f"{Fore.YELLOW}{'─'*80}")
        
        try:
            # Import search agent directly
            from src.modules.agent.search_agent import TavilySearchAgent
            from src.modules.agent.base import AgentState
            from langchain_core.messages import HumanMessage
            
            # Create search agent
            search_agent = TavilySearchAgent(max_results=3)
            
            # Create a simple state for search
            state = AgentState(
                messages=[HumanMessage(content=query)],
                current_agent="search",
                next_agent=None,
                task_description=f"Search for: {query}",
                workflow_stage="processing",
                clarification_needed=False,
                clarification_questions=[],
                user_responses={},
                original_query=query,
                enhanced_query=None,
                analysis_results={},
                retrieval_results=None,
                tool_calls=[],
                tool_results=[],
                session_id=self.current_session or "direct-search",
                user_level="EXPERIENCED"
            )
            
            # Process the search
            response = search_agent.process(state)
            
            if response.error:
                print(f"{Fore.RED}❌ Search error: {response.error}")
            else:
                print(f"{Fore.GREEN}📄 Search Results:")
                # Format the response nicely
                content = response.message
                if "## Web Search Results" in content:
                    content = content.replace("## Web Search Results", "")
                print(f"{Fore.WHITE}{content.strip()}")
                
                # Show metadata
                metadata = response.metadata
                if metadata:
                    print(f"\n{Fore.BLUE}📊 Search Info:")
                    print(f"{Fore.WHITE}   Query: {metadata.get('search_query', 'Unknown')}")
                    print(f"{Fore.WHITE}   Results found: {metadata.get('num_results', 0)}")
        
        except ImportError:
            print(f"{Fore.RED}❌ Search agent not available")
        except Exception as e:
            print(f"{Fore.RED}❌ Search error: {str(e)}")
            if show_header:
                logging.error(f"Direct search error: {e}", exc_info=True)


def main():
    """Run the interactive demo."""
    demo = InteractiveAgentDemo()
    demo.run()


if __name__ == "__main__":
    main()