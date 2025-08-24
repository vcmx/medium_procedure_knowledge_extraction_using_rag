import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.modules.utils.custom_openrouter import ChatOpenRouter


class InventoryCheckAgent:
    def __init__(self, model_name: str, workspace_root: str = None):
        """
        Initializes the InventoryCheckAgent.

        Args:
            model_name: The name of the model to use for the agent.
            workspace_root: The absolute path to the project's root directory.
                            If not provided, it will be inferred by locating
                            the project's root from this file's location.
        """
        self.llm = ChatOpenRouter(
            model_name=model_name,
            temperature=0,
        )

        if workspace_root is None:
            # Infer the project root by going up four levels from the current file
            # This is based on the structure: <root>/src/modules/agent/this_file.py
            self.workspace_root = str(Path(__file__).resolve().parents[3])
            print(
                f"InventoryCheckAgent: Inferred workspace root: {self.workspace_root}"
            )
        else:
            self.workspace_root = workspace_root

    async def process(self, query: str) -> Dict[str, Any]:
        print(f"InventoryCheckAgent: Processing query '{query}' with MCP tool-calling.")

        # Step 1: Configure the MCP client settings.
        client_config = {
            "inventory": {
                "command": "python",
                "args": [f"{self.workspace_root}/src/modules/tools/inventory.py"],
                "transport": "stdio",
            },
        }

        # Following the library's explicit instructions, we instantiate the client
        # and use it directly. The library handles its own cleanup.
        client = MultiServerMCPClient(client_config)

        try:
            # Step 2: Fetch available tools from the MCP server
            mcp_tools = await client.get_tools()
            print(
                "InventoryCheckAgent: Fetched tools from MCP server: "
                f"{[t.name for t in mcp_tools]}"
            )

            # Step 3: Bind these tools to the LLM for this specific call
            llm_with_tools = self.llm.bind_tools(mcp_tools)

            # Step 4: Invoke the LLM, which may decide to call an MCP tool
            ai_msg = await llm_with_tools.ainvoke([HumanMessage(query)])

            # Step 5: Check if the LLM decided to make a tool call
            if not ai_msg.tool_calls:
                print("InventoryCheckAgent: LLM decided not to call a tool.")
                return {
                    "agent": "InventoryCheckAgent",
                    "tool_name": "N/A",
                    "inventory_status": {
                        "error": "Could not determine which tool to check from your query."
                    },
                }

            # Step 6: Execute the tool call requested by the LLM via the MCP client
            tool_call = ai_msg.tool_calls[0]
            print(f"InventoryCheckAgent: LLM initiated tool call: {tool_call['name']}")

            # Find the corresponding tool object to invoke
            target_tool = next(
                (t for t in mcp_tools if t.name == tool_call["name"]), None
            )

            if not target_tool:
                raise ValueError(f"Tool '{tool_call['name']}' not found in MCP tools.")

            # The MCP tool returns a JSON string that we need to parse.
            inventory_status_str = await target_tool.ainvoke(tool_call["args"])
            tool_name_from_llm = tool_call["args"].get("tool_name")

            print(
                f"InventoryCheckAgent: Received status string: {inventory_status_str}"
            )
            inventory_status = json.loads(inventory_status_str)

            return {
                "agent": "InventoryCheckAgent",
                "tool_name": tool_name_from_llm,
                "inventory_status": inventory_status,
            }
        except Exception as e:
            # Handle any exceptions that occur during the process
            print(f"An error occurred in InventoryCheckAgent: {e}")
            return {
                "agent": "InventoryCheckAgent",
                "tool_name": "N/A",
                "inventory_status": {"error": f"An unexpected error occurred: {e}"},
            }


async def main():
    # Example usage:
    # The agent now infers the workspace root automatically.
    agent = InventoryCheckAgent(
        model_name="anthropic/claude-3.5-sonnet",
    )
    result = await agent.process("Do we have a torque wrench in stock?")
    print(result)
    result = await agent.process("Is there a hammer available?")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
