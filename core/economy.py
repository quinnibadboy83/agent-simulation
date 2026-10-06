"""
Economy System
--------------

Tracks simulated and real-capable economic activity.

The economy has two operating modes:

SIMULATION
    Safe internal experimentation.

REAL
    Live-capable mode. Consequential actions remain protected
    by the Creator Approval Gate.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .memory import SharedMemory


class Economy:
    VALID_MODES = {"simulation", "real"}

    def __init__(
        self,
        memory: SharedMemory,
    ):
        self.memory = memory

        world_state = self.memory.data.setdefault(
            "world_state",
            {},
        )

        if world_state.get("economy_mode") not in self.VALID_MODES:
            world_state["economy_mode"] = "simulation"

        world_state.setdefault(
            "opportunities",
            [],
        )

        world_state.setdefault(
            "experiments",
            [],
        )

        self.memory.save()

    # ---------------------------------------------------------
    # MODE
    # ---------------------------------------------------------

    def get_mode(self) -> str:
        return self.memory.get_world_state(
            "economy_mode",
            "simulation",
        )

    def set_mode(self, mode: str) -> str:
        mode = str(mode).strip().lower()

        if mode == "live":
            mode = "real"

        if mode not in self.VALID_MODES:
            raise ValueError(
                "Invalid economy mode. "
                "Use 'simulation' or 'real'."
            )

        self.memory.set_world_state(
            "economy_mode",
            mode,
        )

        self.memory.log(
            "Economy",
            f"Economy mode changed to {mode}.",
        )

        return (
            f"Economy mode set to {mode}."
        )

    def is_simulation(self) -> bool:
        return self.get_mode() == "simulation"

    def is_real(self) -> bool:
        return self.get_mode() == "real"

    def get_mode_policy(self) -> Dict[str, Any]:
        if self.is_simulation():
            return {
                "mode": "simulation",
                "label": "SIMULATION",
                "simulation": True,
                "live": False,
                "live_tools_available": False,
                "protected_actions_allowed": False,
                "creator_approval_required": True,
                "description": (
                    "Safe simulated environment. "
                    "No consequential live-world actions."
                ),
            }

        return {
            "mode": "real",
            "label": "REAL / LIVE",
            "simulation": False,
            "live": True,
            "live_tools_available": True,
            "protected_actions_allowed": True,
            "creator_approval_required": True,
            "description": (
                "Live-capable mode. "
                "Consequential actions still require "
                "explicit Creator approval."
            ),
        }

    def can_use_live_tools(self) -> bool:
        return self.is_real()

    def requires_creator_approval(
        self,
        action: str = "",
    ) -> bool:
        return True

    # ---------------------------------------------------------
    # OPPORTUNITIES
    # ---------------------------------------------------------

    def create_opportunity(
        self,
        name: str,
        description: str,
        startup_cost: float = 0.0,
        expected_expenses: float = 0.0,
        expected_revenue: float = 0.0,
        risk: str = "medium",
    ) -> Dict[str, Any]:

        opportunities = self.memory.data[
            "world_state"
        ].setdefault(
            "opportunities",
            [],
        )

        next_id = 1

        if opportunities:
            ids = []

            for item in opportunities:
                try:
                    ids.append(
                        int(item.get("id", 0))
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

            if ids:
                next_id = max(ids) + 1

        opportunity = {
            "id": next_id,
            "name": name,
            "description": description,
            "startup_cost": float(
                startup_cost
            ),
            "expected_expenses": float(
                expected_expenses
            ),
            "expected_revenue": float(
                expected_revenue
            ),
            "risk": risk,
            "status": "identified",
            "created_at": self._timestamp(),
            "updated_at": self._timestamp(),
        }

        opportunities.append(
            opportunity
        )

        self.memory.save()

        self.memory.log(
            "Economy",
            (
                f"Opportunity created: "
                f"#{next_id} {name}"
            ),
        )

        return opportunity

    def list_opportunities(
        self,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        opportunities = self.memory.data[
            "world_state"
        ].get(
            "opportunities",
            [],
        )

        if status:
            opportunities = [
                item
                for item in opportunities
                if item.get("status") == status
            ]

        return opportunities

    def get_opportunity(
        self,
        opp_id: int,
    ) -> Optional[Dict[str, Any]]:

        for opportunity in self.memory.data[
            "world_state"
        ].get(
            "opportunities",
            [],
        ):
            try:
                current_id = int(
                    opportunity.get(
                        "id",
                        -1,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if current_id == int(opp_id):
                return opportunity

        return None

    def update_opportunity(
        self,
        opp_id: int,
        status: Optional[str] = None,
        **updates,
    ) -> Optional[Dict[str, Any]]:

        opportunity = self.get_opportunity(
            opp_id
        )

        if not opportunity:
            return None

        if status is not None:
            opportunity["status"] = status

        for key, value in updates.items():
            if key in {
                "name",
                "description",
                "startup_cost",
                "expected_expenses",
                "expected_revenue",
                "risk",
            }:
                opportunity[key] = value

        opportunity["updated_at"] = (
            self._timestamp()
        )

        self.memory.save()

        return opportunity

    def analyse_opportunity(
        self,
        opp_id: int,
    ) -> Dict[str, Any]:

        opportunity = self.get_opportunity(
            opp_id
        )

        if not opportunity:
            return {
                "success": False,
                "error": (
                    f"Opportunity #{opp_id} "
                    "not found."
                ),
            }

        startup = float(
            opportunity.get(
                "startup_cost",
                0,
            )
        )

        expenses = float(
            opportunity.get(
                "expected_expenses",
                0,
            )
        )

        revenue = float(
            opportunity.get(
                "expected_revenue",
                0,
            )
        )

        total_cost = (
            startup + expenses
        )

        expected_profit = (
            revenue - total_cost
        )

        if total_cost > 0:
            roi = (
                expected_profit
                / total_cost
            ) * 100
        else:
            roi = 0.0

        risk = str(
            opportunity.get(
                "risk",
                "medium",
            )
        ).lower()

        if expected_profit <= 0:
            recommendation = "reject"

        elif risk == "high":
            recommendation = "review"

        elif roi >= 50:
            recommendation = "strong_candidate"

        else:
            recommendation = "candidate"

        analysis = {
            "success": True,
            "opportunity_id": opportunity[
                "id"
            ],
            "name": opportunity[
                "name"
            ],
            "startup_cost": startup,
            "expected_expenses": expenses,
            "expected_revenue": revenue,
            "total_cost": total_cost,
            "expected_profit": expected_profit,
            "roi_percent": round(
                roi,
                2,
            ),
            "risk": risk,
            "recommendation": recommendation,
        }

        self.memory.log(
            "Economy",
            (
                f"Analysed opportunity "
                f"#{opp_id}: "
                f"{recommendation}"
            ),
        )

        return analysis

    # ---------------------------------------------------------
    # EXPERIMENTS
    # ---------------------------------------------------------

    def create_experiment(
        self,
        opp_id: int,
        budget: float,
        notes: str = "",
    ) -> Dict[str, Any]:

        opportunity = self.get_opportunity(
            opp_id
        )

        if not opportunity:
            return {
                "success": False,
                "error": (
                    f"Opportunity #{opp_id} "
                    "not found."
                ),
            }

        experiments = self.memory.data[
            "world_state"
        ].setdefault(
            "experiments",
            [],
        )

        next_id = 1

        if experiments:
            ids = []

            for item in experiments:
                try:
                    ids.append(
                        int(item.get("id", 0))
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

            if ids:
                next_id = max(ids) + 1

        experiment = {
            "id": next_id,
            "opportunity_id": int(
                opp_id
            ),
            "budget": float(budget),
            "notes": notes,
            "status": "planned",
            "revenue": 0.0,
            "extra_expenses": 0.0,
            "profit": 0.0,
            "created_at": self._timestamp(),
            "completed_at": None,
        }

        experiments.append(
            experiment
        )

        self.memory.save()

        self.memory.log(
            "Economy",
            (
                f"Experiment created: "
                f"#{next_id} for opportunity "
                f"#{opp_id}"
            ),
        )

        return {
            "success": True,
            "experiment": experiment,
        }

    def get_experiment(
        self,
        exp_id: int,
    ) -> Optional[Dict[str, Any]]:

        for experiment in self.memory.data[
            "world_state"
        ].get(
            "experiments",
            [],
        ):
            try:
                current_id = int(
                    experiment.get(
                        "id",
                        -1,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if current_id == int(exp_id):
                return experiment

        return None

    def list_experiments(
        self,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        experiments = self.memory.data[
            "world_state"
        ].get(
            "experiments",
            [],
        )

        if status:
            experiments = [
                item
                for item in experiments
                if item.get("status") == status
            ]

        return experiments

    def complete_experiment(
        self,
        exp_id: int,
        revenue: float,
        extra_expenses: float = 0.0,
        notes: str = "",
    ) -> Dict[str, Any]:

        experiment = self.get_experiment(
            exp_id
        )

        if not experiment:
            return {
                "success": False,
                "error": (
                    f"Experiment #{exp_id} "
                    "not found."
                ),
            }

        if experiment.get("status") == "completed":
            return {
                "success": False,
                "error": (
                    f"Experiment #{exp_id} "
                    "has already been completed."
                ),
            }

        revenue = float(revenue)
        extra_expenses = float(
            extra_expenses
        )

        budget = float(
            experiment.get(
                "budget",
                0,
            )
        )

        profit = (
            revenue
            - budget
            - extra_expenses
        )

        experiment["revenue"] = revenue
        experiment[
            "extra_expenses"
        ] = extra_expenses
        experiment["profit"] = profit
        experiment["status"] = "completed"
        experiment["completed_at"] = (
            self._timestamp()
        )

        if notes:
            experiment["completion_notes"] = (
                notes
            )

        self.memory.save()

        self.memory.log(
            "Economy",
            (
                f"Experiment #{exp_id} "
                f"completed. Profit: "
                f"£{profit:.2f}"
            ),
        )

        return {
            "success": True,
            "experiment": experiment,
            "profit": profit,
        }

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------

    def get_economy_report(
        self,
    ) -> Dict[str, Any]:

        opportunities = self.list_opportunities()
        experiments = self.list_experiments()

        analysed = []

        for opportunity in opportunities:
            analysed.append(
                self.analyse_opportunity(
                    opportunity["id"]
                )
            )

        total_revenue = sum(
            float(
                item.get(
                    "revenue",
                    0,
                )
            )
            for item in experiments
            if item.get("status")
            == "completed"
        )

        total_expenses = sum(
            float(
                item.get(
                    "budget",
                    0,
                )
            )
            + float(
                item.get(
                    "extra_expenses",
                    0,
                )
            )
            for item in experiments
            if item.get("status")
            == "completed"
        )

        realised_profit = (
            total_revenue
            - total_expenses
        )

        return {
            "mode": self.get_mode(),
            "policy": self.get_mode_policy(),
            "opportunities": opportunities,
            "opportunity_count": len(
                opportunities
            ),
            "analyses": analysed,
            "experiments": experiments,
            "experiment_count": len(
                experiments
            ),
            "completed_experiments": len(
                [
                    item
                    for item in experiments
                    if item.get("status")
                    == "completed"
                ]
            ),
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "realised_profit": realised_profit,
        }

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat()
