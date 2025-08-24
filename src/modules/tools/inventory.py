import random
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Inventory",
    "A set of tools to check product inventory.",
)


@mcp.tool()
def check_inventory(tool_name: str) -> Dict[str, Any]:
    """
    Mock function to check tool inventory.

    This function simulates a call to an inventory backend. It returns a
    random availability status for a given tool name. It does not maintain
    state and is designed for demonstration and testing purposes.

    Args:
        tool_name: The name of the tool to check (e.g., "torque wrench").

    Returns:
        A dictionary containing the tool's inventory status.
    """
    if not isinstance(tool_name, str) or not tool_name.strip():
        return {"tool_name": tool_name, "error": "Invalid tool name provided."}

    # Simulate the non-deterministic nature of a real-time inventory check
    is_available = random.choice([True, True, False])  # Skewed towards available

    if is_available:
        quantity = random.randint(1, 50)
        location = random.choice(
            [
                "Warehouse A, Bay 12",
                "Workshop Cabinet 4",
                "Mobile Unit 3",
                "Supply Room 2B",
            ]
        )
        return {
            "tool_name": tool_name,
            "status": "In Stock",
            "quantity": quantity,
            "location": location,
        }
    else:
        estimated_restock_days = random.randint(2, 14)
        return {
            "tool_name": tool_name,
            "status": "Out of Stock",
            "quantity": 0,
            "location": "N/A",
            "note": f"Estimated restock in {estimated_restock_days} days.",
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
