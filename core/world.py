"""
Simulation World State.
"""

from datetime import datetime
from typing import Dict, Any
from .memory import SharedMemory


class World:
    def __init__(self, memory: SharedMemory):
        self.memory = memory
        
        if not self.memory.data.get("world_state"):
            self.memory.data["world_state"] = {
                "day": 1,
                "time_of_day": "Morning",
                "weather": "Clear",
                "resources": {
                    "energy": 100,
                    "info_points": 0,
                    "reputation": 0,
                },
                "locations": {
                    "HQ": {"description": "Main Command Center", "agents_present": ["Boss"]},
                    "DataFarm": {"description": "Information Farming Fields", "agents_present": []},
                    "Vault": {"description": "Secure Storage & Bank", "agents_present": ["Banker"]},
                    "Workshop": {"description": "Tool & Module Workshop", "agents_present": []},
                },
                "started_at": datetime.utcnow().isoformat(),
            }
            self.memory.save()

    @property
    def state(self) -> Dict[str, Any]:
        return self.memory.data["world_state"]

    def advance_time(self):
        order = ["Morning", "Afternoon", "Evening", "Night"]
        current = self.state["time_of_day"]
        idx = order.index(current)
        
        if idx == 3:
            self.state["day"] += 1
            self.state["time_of_day"] = "Morning"
        else:
            self.state["time_of_day"] = order[idx + 1]
        
        self.memory.save()
        self.memory.log("World", f"Time advanced to Day {self.state['day']} - {self.state['time_of_day']}")

    def add_resource(self, resource: str, amount: float):
        if resource in self.state["resources"]:
            self.state["resources"][resource] += amount
            self.memory.save()

    def get_summary(self) -> Dict[str, Any]:
        return {
            "day": self.state["day"],
            "time": self.state["time_of_day"],
            "weather": self.state["weather"],
            "resources": self.state["resources"],
            "locations": self.state["locations"],
        }
