"""
Web Research Tools
Uses Wikipedia API so it works from cloud servers.
"""

from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from .memory import SharedMemory


class WebResearch:
    def __init__(self, memory: SharedMemory):
        self.memory = memory
        self.headers = {
            "User-Agent": "AgentSimulation/1.0 (educational project)"
        }

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results,
                "format": "json",
            }
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(url, params=params, headers=self.headers)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("query", {}).get("search", []):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                snippet = snippet.replace("<span class=\"searchmatch\">", "").replace("</span>", "")
                page_url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
                results.append({
                    "title": title,
                    "url": page_url,
                    "snippet": snippet,
                })

            self.memory.add_knowledge(
                source="WebResearch",
                content=f"Search results for '{query}': {len(results)} found",
                tags=["search", query.lower()],
            )
            for item in results:
                self.memory.add_knowledge(
                    source="WebResearch",
                    content=f"{item['title']} | {item['url']} | {item['snippet']}",
                    tags=["search_result", query.lower()],
                )
            self.memory.log("WebResearch", f"Searched: {query} -> {len(results)} results")
            return results
        except Exception as e:
            self.memory.log("WebResearch", f"Search failed: {str(e)}", level="error")
            return [{"title": "Error", "url": "", "snippet": str(e)}]

    def read_page(self, url: str, max_chars: int = 3000) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(url, headers=self.headers)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)
            if len(clean_text) > max_chars:
                clean_text = clean_text[:max_chars] + "..."

            title = soup.title.string.strip() if soup.title and soup.title.string else url
            result = {
                "url": url,
                "title": title,
                "content": clean_text,
                "length": len(clean_text),
            }
            self.memory.add_knowledge(
                source="WebResearch",
                content=f"Read page: {title} ({url})\n{clean_text[:500]}",
                tags=["page", "research"],
            )
            self.memory.log("WebResearch", f"Read page: {url}")
            return result
        except Exception as e:
            self.memory.log("WebResearch", f"Read page failed: {str(e)}", level="error")
            return {"url": url, "title": "Error", "content": str(e), "length": 0}
