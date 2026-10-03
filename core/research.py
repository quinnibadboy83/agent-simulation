"""
Real Web Research Tools (Module 3)
Allows agents to search the web and read public pages.
Results are stored in SharedMemory so other agents can use them.
"""

from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from .memory import SharedMemory


class WebResearch:
    def __init__(self, memory: SharedMemory):
        self.memory = memory
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AgentSimBot/1.0; +https://example.com/bot)"
        }

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Simple web search using DuckDuckGo HTML (no API key needed).
        Returns a list of {title, url, snippet}
        """
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(url, headers=self.headers)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            for r in soup.select(".result")[:max_results]:
                title_tag = r.select_one(".result__a")
                snippet_tag = r.select_one(".result__snippet")
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                link = title_tag.get("href", "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet
                })

            # Store in shared memory
            self.memory.add_knowledge(
                source="WebResearch",
                content=f"Search results for '{query}': {len(results)} found",
                tags=["search", query.lower()]
            )
            for item in results:
                self.memory.add_knowledge(
                    source="WebResearch",
                    content=f"{item['title']} | {item['url']} | {item['snippet']}",
                    tags=["search_result", query.lower()]
                )

            self.memory.log("WebResearch", f"Searched: {query} → {len(results)} results")
            return results

        except Exception as e:
            self.memory.log("WebResearch", f"Search failed: {str(e)}", level="error")
            return [{"title": "Error", "url": "", "snippet": str(e)}]

    def read_page(self, url: str, max_chars: int = 3000) -> Dict[str, Any]:
        """
        Fetch a public page and extract main text content.
        """
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(url, headers=self.headers)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")

            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            # Get text
            text = soup.get_text(separator="\n", strip=True)
            # Clean excessive newlines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)

            if len(clean_text) > max_chars:
                clean_text = clean_text[:max_chars] + "..."

            title = soup.title.string.strip() if soup.title else url

            result = {
                "url": url,
                "title": title,
                "content": clean_text,
                "length": len(clean_text)
            }

            # Store in memory
            self.memory.add_knowledge(
                source="WebResearch",
                content=f"Read page: {title} ({url})\n{clean_text[:500]}...",
                tags=["page", "research"]
            )
            self.memory.log("WebResearch", f"Read page: {url}")

            return result

        except Exception as e:
            self.memory.log("WebResearch", f"Read page failed: {str(e)}", level="error")
            return {"url": url, "title": "Error", "content": str(e), "length": 0}
