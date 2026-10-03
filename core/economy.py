"""
Module 2 - Autonomous Economy Engine
Supports both SIMULATION and REAL modes.
Banker remains the only financial authority.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .memory import SharedMemory


class Economy:
    def __init__(self, memory: SharedMemory):
        self.memory = memory

        if "economy" not in self.memory.data:
            self.memory.data["economy"] = {
                "mode": "simulation",
                "opportunities": [],
                "experiments": [],
                "next_opportunity_id": 1,
                "next_experiment_id": 1,
            }
            self.memory.save()

    def get_mode(self) -> str:
        return self.memory.data["economy"].get("mode", "simulation")

    def set_mode(self, mode: str) -> str:
        mode = mode.lower().strip()
        if mode not in ["simulation", "real"]:
            return "Invalid mode. Use 'simulation' or 'real'."
        
        old_mode = self.get_mode()
        self.memory.data["economy"]["mode"] = mode
        self.memory.save()
        self.memory.log("Economy", f"Mode changed: {old_mode} → {mode}")
        return f"Economy mode set to: {mode.upper()}"

    def is_simulation(self) -> bool:
        return self.get_mode() == "simulation"

    def is_real(self) -> bool:
        return self.get_mode() == "real"

    def create_opportunity(
        self,
        name: str,
        description: str,
        startup_cost: float,
        expected_expenses: float,
        expected_revenue: float = 0.0,
        risk: str = "medium",
        category: str = "general",
        source: str = "OpportunityAgent",
    ) -> Dict[str, Any]:

        opp_id = self.memory.data["economy"]["next_opportunity_id"]
        self.memory.data["economy"]["next_opportunity_id"] += 1

        opportunity = {
            "id": opp_id,
            "name": name,
            "description": description,
            "startup_cost": float(startup_cost),
            "expected_expenses": float(expected_expenses),
            "expected_revenue": float(expected_revenue),
            "risk": risk,
            "category": category,
            "status": "DISCOVERED",
            "mode": self.get_mode(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "source": source,
            "analysis": {},
            "notes": [],
        }

        self.memory.data["economy"]["opportunities"].append(opportunity)
        self.memory.save()
        self.memory.log("Economy", f"Created opportunity #{opp_id}: {name} [{self.get_mode()}]")
        return opportunity

    def get_opportunity(self, opp_id: int) -> Optional[Dict[str, Any]]:
        for opp in self.memory.data["economy"]["opportunities"]:
            if opp["id"] == opp_id:
                return opp
        return None

    def list_opportunities(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        opps = self.memory.data["economy"]["opportunities"]
        if status:
            opps = [o for o in opps if o["status"] == status]
        return opps

    def update_opportunity_status(self, opp_id: int, new_status: str, notes: str = "") -> Optional[Dict]:
        opp = self.get_opportunity(opp_id)
        if not opp:
            return None
        opp["status"] = new_status
        opp["updated_at"] = datetime.utcnow().isoformat()
        if notes:
            opp["notes"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "text": notes
            })
        self.memory.save()
        self.memory.log("Economy", f"Opportunity #{opp_id} → {new_status}")
        return opp

    def analyse_opportunity(self, opp_id: int) -> Optional[Dict]:
        opp = self.get_opportunity(opp_id)
        if not opp:
            return None

        potential_profit = opp["expected_revenue"] - (opp["startup_cost"] + opp["expected_expenses"])
        total_cost = opp["startup_cost"] + opp["expected_expenses"]
        roi = 0.0
        if total_cost > 0:
            roi = (potential_profit / total_cost) * 100

        analysis = {
            "potential_profit": round(potential_profit, 2),
            "estimated_roi_percent": round(roi, 1),
            "risk_level": opp["risk"],
            "recommendation": "TEST" if potential_profit > 0 and opp["risk"] != "high" else "CAUTION",
            "analysed_at": datetime.utcnow().isoformat(),
            "mode": self.get_mode(),
        }

        opp["analysis"] = analysis
        opp["status"] = "ANALYSED"
        opp["updated_at"] = datetime.utcnow().isoformat()
        self.memory.save()
        self.memory.log("Economy", f"Analysed opportunity #{opp_id}")
        return analysis

    def create_experiment(self, opp_id: int, budget: float, notes: str = "") -> Optional[Dict]:
        opp = self.get_opportunity(opp_id)
        if not opp:
            return None

        exp_id = self.memory.data["economy"]["next_experiment_id"]
        self.memory.data["economy"]["next_experiment_id"] += 1

        experiment = {
            "id": exp_id,
            "opportunity_id": opp_id,
            "budget": float(budget),
            "status": "RUNNING",
            "revenue": 0.0,
            "expenses": float(budget),
            "profit": 0.0,
            "mode": self.get_mode(),
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "notes": notes,
            "results": {},
        }

        self.memory.data["economy"]["experiments"].append(experiment)
        self.update_opportunity_status(opp_id, "TESTING", f"Experiment #{exp_id} started")
        self.memory.save()
        self.memory.log("Economy", f"Started experiment #{exp_id} for opportunity #{opp_id} [{self.get_mode()}]")
        return experiment

    def complete_experiment(self, exp_id: int, revenue: float, extra_expenses: float = 0.0, notes: str = "") -> Optional[Dict]:
        for exp in self.memory.data["economy"]["experiments"]:
            if exp["id"] == exp_id:
                exp["revenue"] = float(revenue)
                exp["expenses"] += float(extra_expenses)
                exp["profit"] = exp["revenue"] - exp["expenses"]
                exp["status"] = "COMPLETED"
                exp["completed_at"] = datetime.utcnow().isoformat()
                if notes:
                    exp["notes"] += " | " + notes

                if exp["profit"] > 0:
                    self.update_opportunity_status(exp["opportunity_id"], "VALIDATED", f"Experiment #{exp_id} profitable")
                else:
                    self.update_opportunity_status(exp["opportunity_id"], "REJECTED", f"Experiment #{exp_id} unprofitable")

                self.memory.save()
                self.memory.log("Economy", f"Completed experiment #{exp_id} | Profit: {exp['profit']}")
                return exp
        return None

    def get_experiment(self, exp_id: int) -> Optional[Dict]:
        for exp in self.memory.data["economy"]["experiments"]:
            if exp["id"] == exp_id:
                return exp
        return None

    def list_experiments(self, status: Optional[str] = None) -> List[Dict]:
        exps = self.memory.data["economy"]["experiments"]
        if status:
            exps = [e for e in exps if e["status"] == status]
        return exps

    def get_economy_report(self) -> Dict[str, Any]:
        opps = self.list_opportunities()
        exps = self.list_experiments()

        total_revenue = sum(e["revenue"] for e in exps)
        total_expenses = sum(e["expenses"] for e in exps)
        total_profit = total_revenue - total_expenses

        return {
            "mode": self.get_mode().upper(),
            "opportunities_total": len(opps),
            "opportunities_by_status": {
                "DISCOVERED": len([o for o in opps if o["status"] == "DISCOVERED"]),
                "ANALYSED": len([o for o in opps if o["status"] == "ANALYSED"]),
                "TESTING": len([o for o in opps if o["status"] == "TESTING"]),
                "VALIDATED": len([o for o in opps if o["status"] == "VALIDATED"]),
                "REJECTED": len([o for o in opps if o["status"] == "REJECTED"]),
            },
            "experiments_total": len(exps),
            "total_revenue": round(total_revenue, 2),
            "total_expenses": round(total_expenses, 2),
            "total_profit": round(total_profit, 2),
            "active_experiments": len([e for e in exps if e["status"] == "RUNNING"]),
        }
