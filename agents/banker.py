"""
Banker Agent
------------

Financial Controller for the agent simulation.

The Banker:
- monitors the shared balance
- records financial activity
- reports transactions
- does not bypass the Creator approval system
- does not directly execute consequential financial actions
"""

from typing import Any, Dict, List

from .base_agent import BaseAgent
from core.memory import SharedMemory
from core.tools import ToolRegistry


class BankerAgent(BaseAgent):

    def __init__(
        self,
        memory: SharedMemory,
        tools: ToolRegistry,
    ):
        super().__init__(
            name="Banker",
            role="Financial Controller",
            memory=memory,
            tools=tools,
            description=(
                "Manages financial records, "
                "monitors balances and reports "
                "income and expenses."
            ),
        )

        self.update_status("ready")

        # Open the Banker account only when one
        # does not already exist.
        if not self._has_transactions():
            memory.add_transaction(
                0.0,
                "System",
                "Banker",
                "Initial account opened",
            )

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def process_order(
        self,
        order: str,
    ) -> str:

        self.memory.log(
            "Banker",
            f"Received order: {order}",
        )

        order_text = order.strip()
        order_lower = order_text.lower()

        if not order_text:
            return (
                "Banker needs a financial instruction."
            )

        # --------------------------------------------------------------
        # Balance
        # --------------------------------------------------------------

        if (
            "balance" in order_lower
            or "money" in order_lower
        ):
            return self._balance_report()

        # --------------------------------------------------------------
        # Report
        # --------------------------------------------------------------

        if "report" in order_lower:
            return self._financial_report()

        # --------------------------------------------------------------
        # Transactions
        # --------------------------------------------------------------

        if (
            "transaction" in order_lower
            or "transactions" in order_lower
            or "ledger" in order_lower
        ):
            return self._transaction_report()

        # --------------------------------------------------------------
        # Allowance
        # --------------------------------------------------------------

        if "allowance" in order_lower:
            return (
                "Allowance system ready.\n"
                "Financial actions remain subject "
                "to the Creator approval system."
            )

        return (
            f"Banker acknowledging order: "
            f"'{order_text}'.\n"
            "Try: balance, report, "
            "transactions or allowance."
        )

    # ------------------------------------------------------------------
    # Balance
    # ------------------------------------------------------------------

    def _balance_report(
        self,
    ) -> str:

        balance = self.memory.get_balance(
            "Banker"
        )

        return (
            "Banker Balance\n"
            "--------------\n"
            f"Current Balance: "
            f"${balance:.2f}"
        )

    # ------------------------------------------------------------------
    # Financial report
    # ------------------------------------------------------------------

    def _financial_report(
        self,
    ) -> str:

        balance = self.memory.get_balance(
            "Banker"
        )

        transactions = self.memory.data.get(
            "transactions",
            [],
        )

        income = 0.0
        expenses = 0.0

        for transaction in transactions:

            amount = float(
                transaction.get(
                    "amount",
                    0.0,
                )
            )

            if transaction.get("to") == "Banker":
                income += amount

            if transaction.get("from") == "Banker":
                expenses += amount

        return (
            "=== BANKER REPORT ===\n"
            f"Current Balance: ${balance:.2f}\n"
            f"Total Inflows:   ${income:.2f}\n"
            f"Total Outflows:  ${expenses:.2f}\n"
            f"Transactions:    {len(transactions)}"
        )

    # ------------------------------------------------------------------
    # Transaction report
    # ------------------------------------------------------------------

    def _transaction_report(
        self,
    ) -> str:

        transactions = self.memory.data.get(
            "transactions",
            [],
        )

        if not transactions:
            return (
                "No financial transactions recorded."
            )

        recent = transactions[-10:]

        report = (
            "Recent Transactions\n"
            "--------------------\n"
        )

        for transaction in recent:

            timestamp = str(
                transaction.get(
                    "timestamp",
                    "",
                )
            )[:16]

            amount = float(
                transaction.get(
                    "amount",
                    0.0,
                )
            )

            sender = transaction.get(
                "from",
                "Unknown",
            )

            receiver = transaction.get(
                "to",
                "Unknown",
            )

            reason = transaction.get(
                "reason",
                "",
            )

            report += (
                f"{timestamp} | "
                f"{amount:+.2f} | "
                f"{sender} -> {receiver} | "
                f"{reason}\n"
            )

        return report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _has_transactions(
        self,
    ) -> bool:

        transactions = self.memory.data.get(
            "transactions",
            [],
        )

        for transaction in transactions:
            if (
                transaction.get("to")
                == "Banker"
            ):
                return True

            if (
                transaction.get("from")
                == "Banker"
            ):
                return True

        return False
