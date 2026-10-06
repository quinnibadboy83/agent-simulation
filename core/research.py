"""
Web Research
------------
Read-only public web research for the agent simulation.

The research system can:
- Search public information.
- Read public webpages.
- Extract useful text.
- Store findings in shared memory.

It does not perform consequential external actions.
"""

from typing import Any, Dict, List
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup


class WebResearch:
    def __init__(
        self,
        memory,
        timeout: float = 15.0,
    ):
        self.memory = memory
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        query = (query or "").strip()

        if not query:
            return {
                "status": "error",
                "message": "Search query cannot be empty.",
            }

        limit = max(1, min(int(limit), 20))

        encoded_query = quote(query)

        url = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=query"
            f"&list=search"
            f"&srsearch={encoded_query}"
            f"&format=json"
            f"&srlimit={limit}"
            f"&utf8=1"
        )

        try:
            response = httpx.get(
                url,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "AgentSimulation/1.0 "
                        "(read-only research client)"
                    )
                },
            )

            response.raise_for_status()

            data = response.json()

            search_results = data.get("query", {}).get(
                "search",
                [],
            )

            results: List[Dict[str, Any]] = []

            for item in search_results:
                title = item.get("title", "")
                snippet = BeautifulSoup(
                    item.get("snippet", ""),
                    "html.parser",
                ).get_text(" ", strip=True)

                page_url = (
                    "https://en.wikipedia.org/wiki/"
                    + quote(title.replace(" ", "_"))
                )

                results.append(
                    {
                        "title": title,
                        "snippet": snippet,
                        "url": page_url,
                    }
                )

            result = {
                "status": "success",
                "query": query,
                "source": "Wikipedia",
                "count": len(results),
                "results": results,
            }

            self._store_search(query, result)

            self._log(
                "web_search",
                {
                    "query": query,
                    "count": len(results),
                },
            )

            return result

        except httpx.HTTPError as exc:
            return {
                "status": "error",
                "query": query,
                "message": f"Web request failed: {exc}",
            }

        except Exception as exc:
            return {
                "status": "error",
                "query": query,
                "message": f"Research failed: {exc}",
            }

    # ------------------------------------------------------------------
    # Read webpage
    # ------------------------------------------------------------------

    def read_page(
        self,
        url: str,
        max_chars: int = 12000,
    ) -> Dict[str, Any]:
        url = (url or "").strip()

        if not url:
            return {
                "status": "error",
                "message": "URL cannot be empty.",
            }

        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            return {
                "status": "error",
                "url": url,
                "message": "Only HTTP and HTTPS URLs are supported.",
            }

        max_chars = max(1000, min(int(max_chars), 50000))

        try:
            response = httpx.get(
                url,
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "AgentSimulation/1.0 "
                        "(read-only research client)"
                    )
                },
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "content-type",
                "",
            ).lower()

            if (
                "text/html" not in content_type
                and "application/xhtml" not in content_type
            ):
                return {
                    "status": "error",
                    "url": url,
                    "message": (
                        "The requested resource is not an HTML page."
                    ),
                    "content_type": content_type,
                }

            soup = BeautifulSoup(
                response.text,
                "lxml",
            )

            title = ""

            if soup.title:
                title = soup.title.get_text(
                    " ",
                    strip=True,
                )

            for element in soup(
                [
                    "script",
                    "style",
                    "noscript",
                    "nav",
                    "footer",
                    "header",
                    "aside",
                    "form",
                ]
            ):
                element.decompose()

            main = (
                soup.find("main")
                or soup.find("article")
                or soup.body
                or soup
            )

            text = self._clean_text(
                main.get_text(
                    "\n",
                    strip=True,
                )
            )

            truncated = len(text) > max_chars

            if truncated:
                text = text[:max_chars].rstrip()

            result = {
                "status": "success",
                "url": url,
                "final_url": str(response.url),
                "title": title,
                "content": text,
                "characters": len(text),
                "truncated": truncated,
            }

            self._store_page_knowledge(
                url,
                result,
            )

            self._log(
                "read_webpage",
                {
                    "url": url,
                    "title": title,
                    "characters": len(text),
                },
            )

            return result

        except httpx.HTTPError as exc:
            return {
                "status": "error",
                "url": url,
                "message": f"Web request failed: {exc}",
            }

        except Exception as exc:
            return {
                "status": "error",
                "url": url,
                "message": f"Page reading failed: {exc}",
            }

    # ------------------------------------------------------------------
    # Research topic
    # ------------------------------------------------------------------

    def research_topic(
        self,
        topic: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        topic = (topic or "").strip()

        if not topic:
            return {
                "status": "error",
                "message": "Research topic cannot be empty.",
            }

        search_result = self.search(
            query=topic,
            limit=limit,
        )

        if search_result.get("status") != "success":
            return search_result

        return {
            "status": "success",
            "topic": topic,
            "search": search_result,
            "message": (
                f"Research completed for '{topic}'."
            ),
        }

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def _store_search(
        self,
        query: str,
        result: Dict[str, Any],
    ) -> None:
        try:
            if hasattr(self.memory, "add_knowledge"):
                self.memory.add_knowledge(
                    key=f"search:{query}",
                    value=result,
                )
        except Exception:
            pass

    def _store_page_knowledge(
        self,
        url: str,
        result: Dict[str, Any],
    ) -> None:
        try:
            if hasattr(self.memory, "add_knowledge"):
                self.memory.add_knowledge(
                    key=f"page:{url}",
                    value=result,
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Text cleanup
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(text: str) -> str:
        lines = []

        for line in text.splitlines():
            cleaned = " ".join(line.split())

            if cleaned:
                lines.append(cleaned)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(
        self,
        event: str,
        data: Dict[str, Any],
    ) -> None:
        try:
            if hasattr(self.memory, "log"):
                self.memory.log(
                    event,
                    data,
                )
        except Exception:
            pass
