"""
Banker Agent - Manages money and allowances.
"""

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry


class BankerAgent(BaseAgent):
    def __init__(self, memory: SharedMemory, tools: ToolRegistry):
        super().__init__(
            name="Banker",
            role="Financial Controller",
            memory=memory,
            tools=tools,
            description="Manages all money. Receives allowances and rules from the Boss. Tracks income and expenses.",
        )
        self.update_status("ready")
        
        if memory.get_balance("Banker") == 0:
            memory.add_transaction(0.0, "System", "Banker", "Initial account opened")

    def process_order(self, order: str) -> str:
        order_lower = order.lower()
        self.memory.log("Banker", f"Received order: {order}")

        if "balance" in order_lower or "report" in order_lower:
            bal = self.memory.get_balance("Banker")
            txs = self.memory.data.get("transactions", [])[-5:]
            report = f"Banker Report\nCurrent Balance: ${bal:.2f}\n\nRecent transactions:\n"
            for tx in txs:
                report += f"  {tx['timestamp'][:16]} | {tx['amount']:+.2f} | {tx['reason']}\n"
            return report

        if "allowance" in order_lower:
            return "Allowance system ready. Tell me the amount and which agent when you want to set one."

        return f"Banker acknowledging order: '{order}'. Awaiting specific financial instructions."
