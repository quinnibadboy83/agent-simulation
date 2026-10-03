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

        # Initialise economy section if missing
        if "economy" not in self.memory.data:
            self.memory.data["economy"] = {
                "mode": "simulation",          # "simulation" or "real"
                "opportunities": [],
                "experiments": [],
                "next_opportunity_id": 1,
                "next_experiment_id": 1,
            }
            self.memory.save()

    # ------------------------------------------------------------------
    # Mode management
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Opportunity management
    # ------------------------------------------------------------------
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
            "risk": risk,                    # low / medium / high
            "category": category,
            "status": "DISCOVERED",          # DISCOVERED → ANALYSED → TESTING → VALIDATED → REJECTED
            "mode": self.get_mode(),         # record which mode it was created in
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
        """Basic analysis (works in both modes)."""
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

    # ------------------------------------------------------------------
    # Experiment management
    # ------------------------------------------------------------------
    def create_experiment(self, opp_id: int, budget: float, notes: str = "") -> Optional[Dict]:
        opp = self.get_opportunity(opp_id)
        if not opp:
            return None
