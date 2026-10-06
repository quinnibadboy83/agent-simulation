"""
Optional extension modules for the agent simulation.

These modules provide higher-level strategy capabilities while leaving
actual consequential execution to the core ToolRegistry and Creator
approval system.
"""

from .revenue import RevenueStrategy
from .social import SocialStrategy

__all__ = [
    "RevenueStrategy",
    "SocialStrategy",
]
