"""
Banker Agent
------------
Financial and economy specialist for the agent simulation.

The Banker handles balances, simulated transactions, financial reports,
budgets, and economy information. It does not independently perform
real-world financial transactions.
"""

from typing import Any, Dict

from .base_agent import BaseAgent


class Banker(BaseAgent):
    def __init__(self, memory, tools):
        super().__init__(
            name="Banker",
            role="Finance and Economy",
            memory=memory,
            tools=tools,
            description=(
                "Tracks simulated finances, reports balances and "
                "transactions, evaluates budgets, and supports the "
                "economic planning of the agent system."
            ),
        )

    def process_order(self, order: str) -> Dict[str, Any]:
        command = (order or "").strip()

        if not command:
            return {
                "status": "error",
                "agent": self.name,
                "message": "No banking order supplied.",
            }

        lowered = command.lower()

        if lowered in {"help", "?", "commands"}:
            return self.get_help()

        if lowered in {
            "balance",
            "money",
            "funds",
            "check balance",
            "check funds",
        }:
            return self._balance_report()

        if lowered in {
            "report",
            "finance",
            "financial report",
            "economy",
        }:
            return self._financial_report()

        if lowered in {
            "transactions",
            "transaction",
            "ledger",
            "history",
        }:
            return self._transaction_report()

        if lowered in {
            "allowance",
            "budget",
            "spending limit",
        }:
            return self._allowance_report()

        if lowered in {
            "status",
            "agent status",
        }:
            return self.get_status_report()

        if lowered in {
            "run",
            "cycle",
            "run cycle",
        }:
            return self.run_cycle()

        if lowered.startswith("income "):
            value_text = command[7:].strip()

            try:
                amount = float(value_text)
            except ValueError:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Income amount must be numeric.",
                }

            return self.record_simulated_income(amount)

        if lowered.startswith("expense "):
            value_text = command[8:].strip()

            try:
                amount = float(value_text)
            except ValueError:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": "Expense amount must be numeric.",
                }

            return self.record_simulated_expense(amount)

        return {
            "status": "error",
            "agent": self.name,
            "message": f"Unknown Banker command: {command}",
            "help": self.get_help(),
        }

    def _balance_report(self) -> Dict[str, Any]:
        try:
            balance = self.memory.get_balance()
        except Exception as exc:
            return {
                "status": "error",
                "agent": self.name,
                "message": f"Unable to read balance: {exc}",
            }

        return {
            "status": "success",
            "agent": self.name,
            "operation": "balance",
            "balance": balance,
            "currency": "SIM",
            "mode": "simulation",
        }

    def _financial_report(self) -> Dict[str, Any]:
        try:
            balance = self.memory.get_balance()
        except Exception:
            balance = 0.0

        try:
            transactions = self.memory.get_transactions()
        except Exception:
            transactions = []

        income = 0.0
        expenses = 0.0

        for transaction in transactions:
            if not isinstance(transaction, dict):
                continue

            transaction_type = str(
                transaction.get("type", "")
            ).lower()

            try:
                amount = float(transaction.get("amount", 0.0))
            except (TypeError, ValueError):
                amount = 0.0

            if transaction_type in {"income", "credit", "deposit"}:
                income += amount

            elif transaction_type in {
                "expense",
                "debit",
                "withdrawal",
            }:
                expenses += amount

        return {
            "status": "success",
            "agent": self.name,
            "operation": "financial_report",
            "currency": "SIM",
            "balance": balance,
            "total_income": income,
            "total_expenses": expenses,
            "net_flow": income - expenses,
            "transaction_count": len(transactions),
            "mode": "simulation",
        }

    def _transaction_report(self) -> Dict[str, Any]:
        try:
            transactions = self.memory.get_transactions()
        except Exception as exc:
            return {
                "status": "error",
                "agent": self.name,
                "message": f"Unable to read transactions: {exc}",
            }

        return {
            "status": "success",
            "agent": self.name,
            "operation": "transactions",
            "transactions": transactions,
            "count": len(transactions),
        }

    def _allowance_report(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "operation": "allowance",
            "policy": {
                "mode": "simulation",
                "real_world_spending": False,
                "creator_approval_required": True,
                "autonomous_financial_transactions": False,
            },
            "message": (
                "The Banker can analyse and simulate finances, but "
                "cannot independently spend real money."
            ),
        }

    def record_simulated_income(
        self,
        amount: float,
        source: str = "simulated_income",
    ) -> Dict[str, Any]:
        if amount <= 0:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Income amount must be greater than zero.",
            }

        try:
            transaction = self.memory.add_transaction(
                transaction_type="income",
                amount=amount,
                description=source,
                agent=self.name,
            )
        except TypeError:
            try:
                transaction = self.memory.add_transaction(
                    {
                        "type": "income",
                        "amount": amount,
                        "description": source,
                        "agent": self.name,
                    }
                )
            except Exception as exc:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": f"Unable to record income: {exc}",
                }
        except Exception as exc:
            return {
                "status": "error",
                "agent": self.name,
                "message": f"Unable to record income: {exc}",
            }

        return {
            "status": "success",
            "agent": self.name,
            "operation": "simulated_income",
            "amount": amount,
            "transaction": transaction,
            "simulation_only": True,
        }

    def record_simulated_expense(
        self,
        amount: float,
        description: str = "simulated_expense",
    ) -> Dict[str, Any]:
        if amount <= 0:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Expense amount must be greater than zero.",
            }

        try:
            balance = self.memory.get_balance()
        except Exception:
            balance = 0.0

        if amount > balance:
            return {
                "status": "error",
                "agent": self.name,
                "message": "Insufficient simulated balance.",
                "balance": balance,
                "requested": amount,
            }

        try:
            transaction = self.memory.add_transaction(
                transaction_type="expense",
                amount=amount,
                description=description,
                agent=self.name,
            )
        except TypeError:
            try:
                transaction = self.memory.add_transaction(
                    {
                        "type": "expense",
                        "amount": amount,
                        "description": description,
                        "agent": self.name,
                    }
                )
            except Exception as exc:
                return {
                    "status": "error",
                    "agent": self.name,
                    "message": f"Unable to record expense: {exc}",
                }
        except Exception as exc:
            return {
                "status": "error",
                "agent": self.name,
                "message": f"Unable to record expense: {exc}",
            }

        return {
            "status": "success",
            "agent": self.name,
            "operation": "simulated_expense",
            "amount": amount,
            "transaction": transaction,
            "simulation_only": True,
        }

    def get_help(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "agent": self.name,
            "role": self.role,
            "commands": [
                "balance",
                "money",
                "funds",
                "report",
                "finance",
                "economy",
                "transactions",
                "ledger",
                "allowance",
                "budget",
                "income <amount>",
                "expense <amount>",
                "status",
                "run",
                "help",
            ],
            "capabilities": [
                "Balance reporting",
                "Financial reporting",
                "Transaction tracking",
                "Budget policy reporting",
                "Simulated income",
                "Simulated expenses",
                "Economy analysis",
            ],
            "safety": (
                "Banker operates on the simulation economy. "
                "Real financial transactions require Creator approval "
                "through the protected action system."
            ),
        }



