"""
Banker Agent
------------

Financial controller for the agent system.

The Banker:
- monitors balances
- reports transactions
- maintains financial awareness
- can create simulated financial records
- cannot bypass Creator approval for consequential actions
"""

from typing import Any, Dict, Optional

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
                "Tracks balances, transactions "
                "and financial state."
            ),
            identity=(
                "You are Banker, the financial controller "
                "of the agent system. You monitor money, "
                "maintain accurate records and report "
                "financial state. You never fabricate "
                "transactions and never bypass Creator "
                "approval."
            ),
        )

    # ======================================================
    # COMMAND PROCESSING
    # ======================================================

    def process_order(
        self,
        command: str,
    ) -> Any:

        command = str(command).strip()

        if not command:
            return self.get_help()

        self.perceive(
            command,
            source="boss",
        )

        lowered = command.lower()

        # --------------------------------------------------
        # HELP
        # --------------------------------------------------

        if lowered in {
            "help",
            "?",
        }:
            return self.get_help()

        # --------------------------------------------------
        # BALANCE
        # --------------------------------------------------

        if (
            lowered == "balance"
            or lowered == "money"
            or lowered == "funds"
        ):
            return self._balance_report()

        # --------------------------------------------------
        # REPORT
        # --------------------------------------------------

        if (
            lowered in {
                "report",
                "financial report",
                "finance",
                "financial status",
            }
        ):
            return self._financial_report()

        # --------------------------------------------------
        # TRANSACTIONS
        # --------------------------------------------------

        if (
            lowered.startswith(
                "transactions"
            )
            or lowered.startswith(
                "transaction"
            )
            or lowered == "ledger"
        ):
            return self._transaction_report()

        # --------------------------------------------------
        # ALLOWANCE
        # --------------------------------------------------

        if (
            lowered.startswith(
                "allowance"
            )
            or lowered.startswith(
                "budget"
            )
        ):
            return self._allowance_report()

        # --------------------------------------------------
        # STATUS
        # --------------------------------------------------

        if lowered == "status":
            return self.get_status_report()

        # --------------------------------------------------
        # GENERIC FINANCIAL REASONING
        # --------------------------------------------------

        return self.run_cycle(
            command
        )

    # ======================================================
    # REPORTS
    # ======================================================

    def _balance_report(
        self,
    ) -> Dict[str, Any]:

        balance = self.memory.get_balance(
            "Banker"
        )

        return {
            "success": True,
            "agent": self.name,
            "balance": balance,
            "currency": "GBP",
            "formatted": (
                f"£{balance:.2f}"
            ),
        }

    def _financial_report(
        self,
    ) -> Dict[str, Any]:

        balance = self.memory.get_balance(
            "Banker"
        )

        transactions = self.memory.data.get(
            "transactions",
            [],
        )

        incoming = 0.0
        outgoing = 0.0

        for transaction in transactions:

            amount = float(
                transaction.get(
                    "amount",
                    0.0,
                )
            )

            if transaction.get(
                "to"
            ) == "Banker":
                incoming += amount

            if transaction.get(
                "from"
            ) == "Banker":
                outgoing += amount

        return {
            "success": True,
            "agent": self.name,
            "currency": "GBP",
            "balance": balance,
            "incoming": incoming,
            "outgoing": outgoing,
            "transaction_count": len(
                transactions
            ),
            "net_flow": (
                incoming - outgoing
            ),
        }

    def _transaction_report(
        self,
    ) -> Dict[str, Any]:

        transactions = self.memory.data.get(
            "transactions",
            [],
        )

        return {
            "success": True,
            "agent": self.name,
            "count": len(
                transactions
            ),
            "transactions": transactions[
                -50:
            ],
        }

    def _allowance_report(
        self,
    ) -> Dict[str, Any]:

        balance = self.memory.get_balance(
            "Banker"
        )

        return {
            "success": True,
            "agent": self.name,
            "available_balance": balance,
            "currency": "GBP",
            "note": (
                "Consequential spending requires "
                "an exact Creator-approved action."
            ),
        }

    # ======================================================
    # FINANCIAL OPERATIONS
    # ======================================================

    def record_simulated_income(
        self,
        amount: float,
        source: str,
        reason: str = "",
    ):

        amount = float(amount)

        if amount <= 0:
            return {
                "success": False,
                "error": (
                    "Income must be greater than zero."
                ),
            }

        transaction = (
            self.memory.add_transaction(
                amount=amount,
                from_agent=source,
                to_agent="Banker",
                reason=(
                    reason
                    or "Simulated income"
                ),
            )
        )

        return {
            "success": True,
            "transaction": transaction,
            "balance": (
                self.memory.get_balance(
                    "Banker"
                )
            ),
        }

    def record_simulated_expense(
        self,
        amount: float,
        recipient: str,
        reason: str = "",
    ):

        amount = float(amount)

        if amount <= 0:
            return {
                "success": False,
                "error": (
                    "Expense must be greater than zero."
                ),
            }

        balance = self.memory.get_balance(
            "Banker"
        )

        if amount > balance:
            return {
                "success": False,
                "error": (
                    "Insufficient simulated funds."
                ),
                "balance": balance,
            }

        transaction = (
            self.memory.add_transaction(
                amount=amount,
                from_agent="Banker",
                to_agent=recipient,
                reason=(
                    reason
                    or "Simulated expense"
                ),
            )
        )

        return {
            "success": True,
            "transaction": transaction,
            "balance": (
                self.memory.get_balance(
                    "Banker"
                )
            ),
        }

    # ======================================================
    # STATUS / HELP
    # ======================================================

    def get_help(self):

        return (
            "Banker commands:\n"
            "balance\n"
            "report\n"
            "transactions\n"
            "ledger\n"
            "allowance\n"
            "status\n\n"
            "The Banker tracks financial state. "
            "Consequential spending requires "
            "Creator approval."
        )
