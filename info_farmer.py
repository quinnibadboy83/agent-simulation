"""
InfoFarmer Agent - Farms information, stores it, and feeds it to other agents.
"""

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry


class InfoFarmerAgent(BaseAgent):
    def __init__(self, memory: SharedMemory, tools: ToolRegistry):
        super().__init__(
            name="InfoFarmer",
            role="Information Specialist",
            memory=memory,
            tools=tools,
            description="Farms knowledge from the world, stores it, and supplies other agents with useful information.",
        )
        self.update_status("ready")

    def process_order(self, order: str) -> str:
        self.memory.log("InfoFarmer", f"Received order: {order}")
        
        # Extract topic roughly
        topic = order
        for word in ["farm", "research", "find", "gather", "info", "about", "on"]:
            topic = topic.replace(word, "")
        topic = topic.strip() or "general market opportunities"

        result = self.execute_tool("farm_info", topic=topic, agent=self.name)
        
        if result.get("success"):
            entry = result["result"]
            return f"InfoFarmer completed task.\nFarmed knowledge #{entry['id']}:\n{entry['content']}"
        else:
            return f"InfoFarmer failed: {result.get('error')}"
