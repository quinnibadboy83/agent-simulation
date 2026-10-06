"""
Core simulation package.

Provides shared memory, world state, cognitive rooms,
approval control, tools, economy, research, and orchestration.
"""

from .memory import SharedMemory
from .world import World
from .cognitive_room import CognitiveRoom
from .approvals import ApprovalGate
from .tools import ToolRegistry, create_default_tools
from .economy import Economy
from .research import WebResearch
from .orchestrator import Orchestrator

__all__ = [
    "SharedMemory",
    "World",
    "CognitiveRoom",
    "ApprovalGate",
    "ToolRegistry",
    "create_default_tools",
    "Economy",
    "WebResearch",
    "Orchestrator",
]
