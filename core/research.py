"""
Web Research
------------
Read-only public web research service.

This module provides:
- Search
- Webpage retrieval
- Basic HTML extraction
- Knowledge persistence

It does not perform consequential external actions.
"""

from typing import Any, Dict, List
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from .memory import SharedMemory


class WebResearch:
    def __init__(
        self,
        memory: SharedMemory,
        timeout: float = 15.0,
    ):
        self.memory = memory
        self.timeout = timeout

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        query = (query or "").strip()

        if not query:
            return {
                "status": "error",
                "message": "Search query is required.",
                "results": [],
            }

        try:
            limit = max(1, min(int(limit), 20))
        except (TypeError, ValueError):
            limit = 5

        url = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=query"
            f"&list=search"
            f"&srsearch={quote(query)}"
            f"&format=json"
            f"&utf8=1"
            f"&srlimit={
