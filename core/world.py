"""
Simulation World State
----------------------
Shared physical/environmental state for the agent simulation.
"""

from datetime import datetime
from typing import Any, Dict

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
                    "HQ": {
                        "description": "Main Command Center",
                        "agents_present": ["Boss"],
                    },
                    "DataFarm": {
                        "description": "Information Farming Fields",
                        "agents_present": [],
                    },
                    "Vault": {
                        "description": "Secure Storage & Bank",
                        "agents_present": ["Banker"],
                    },
                    "Workshop": {
                        "description": "Tool & Module Workshop",
                        "agents_present": [],
                    },
                },
                "started_at": datetime.utcnow().isoformat(),
            }

            self.memory.save()

    @property
    def state(self) -> Dict[str, Any]:
        return self.memory.data["world_state"]

    def advance_time(self) -> Dict[str, Any]:
        order = [
            "Morning",
            "Afternoon",
            "Evening",
            "Night",
        ]

        current = self.state.get("time_of_day", "Morning")

        if current not in order:
            current = "Morning"

        index = order.index(current)

        if index == len(order) - 1:
            self.state["day"] = int(self.state.get("day", 1)) + 1
            self.state["time_of_day"] = "Morning"
        else:
            self.state["time_of_day"] = order[index + 1]

        self.memory.save()

        message = (
            f"Time advanced to Day "
            f"{self.state['day']} - "
            f"{self.state['time_of_day']}"
        )

        self.memory.log("World", message)

        return {
            "status": "success",
            "day": self.state["day"],
            "time_of_day": self.state["time_of_day"],
            "message": message,
        }

    def add_resource(self, resource: str, amount: float) -> Dict[str, Any]:
        resources = self.state.setdefault("resources", {})

        if resource not in resources:
            resources[resource] = 0

        resources[resource] += amount

        self.memory.save()

        return {
            "status": "success",
            "resource": resource,
            "amount_added": amount,
            "new_value": resources[resource],
        }

    def remove_resource(self, resource: str, amount: float) -> Dict[str, Any]:
        resources = self.state.setdefault("resources", {})

        if resource not in resources:
            return {
                "status": "error",
                "message": f"Unknown resource: {resource}",
            }

        current = resources[resource]

        if current < amount:
            return {
                "status": "error",
                "message": (
                    f"Insufficient {resource}. "
                    f"Available: {current}, requested: {amount}"
                ),
            }

        resources[resource] -= amount

        self.memory.save()

        return {
            "status": "success",
            "resource": resource,
            "amount_removed": amount,
            "new_value": resources[resource],
        }

    def get_resource(self, resource: str) -> float:
        return float(
            self.state
            .setdefault("resources", {})
            .get(resource, 0)
        )

    def move_agent(
        self,
        agent_name: str,
        destination: str,
    ) -> Dict[str, Any]:
        locations = self.state.setdefault("locations", {})

        if destination not in locations:
            return {
                "status": "error",
                "message": f"Unknown location: {destination}",
            }

        for location in locations.values():
            agents = location.setdefault("agents_present", [])

            if agent_name in agents:
                agents.remove(agent_name)

        destination_agents = locations[destination].setdefault(
            "agents_present",
            [],
        )

        if agent_name not in destination_agents:
            destination_agents.append(agent_name)

        self.memory.save()

        return {
            "status": "success",
            "agent": agent_name,
            "location": destination,
        }

    def get_agent_location(self, agent_name: str) -> str:
        for location_name, location in self.state.get(
            "locations",
            {},
        ).items():
            if agent_name in location.get("agents_present", []):
                return location_name

        return "Unknown"

    def set_weather(self, weather: str) -> Dict[str, Any]:
        weather = (weather or "").strip()

        if not weather:
            return {
                "status": "error",
                "message": "Weather value is required.",
            }

        self.state["weather"] = weather
        self.memory.save()

        return {
            "status": "success",
            "weather": weather,
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            "day": self.state.get("day", 1),
            "time": self.state.get("time_of_day", "Morning"),
            "weather": self.state.get("weather", "Clear"),
            "resources": dict(
                self.state.get("resources", {})
            ),
            "locations": dict(
                self.state.get("locations", {})
            ),
        }
