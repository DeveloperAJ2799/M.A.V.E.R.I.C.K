"""Search tool for web lookups."""

import requests
import re
from typing import Any, Dict
from urllib.parse import quote, unquote
from .base import Tool, ToolResult


class SearchTool(Tool):
    """Tool for searching the web - uses Bing (free, unlimited)."""

    def __init__(self):
        super().__init__(
            name="search",
            description="Search the web for current information. Returns titles, URLs and snippets.",
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    async def execute(self, query: str, **kwargs) -> ToolResult:
        if not query:
            return ToolResult(success=False, result=None, error="No search query provided")
        
        results = await self._search_bing(query)
        
        if results:
            return ToolResult(success=True, result=results)
        else:
            return ToolResult(success=False, result=None, error="No search results found. Try a different query.")

    async def _search_bing(self, query: str) -> str:
        """Search using Bing."""
        try:
            url = f"https://www.bing.com/search?q={quote(query)}"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                return None
            
            return self._parse_bing_results(response.text)
            
        except Exception:
            return None

    def _parse_bing_results(self, html: str) -> str:
        """Parse Bing search results - working extraction."""
        results = []
        
        # Find h2 tags which contain result titles
        h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
        
        import html as html_module
        for h2_content in h2_matches[:10]:
            # Extract text from within the h2
            title_match = re.search(r'>([^<]+)<', h2_content)
            if not title_match:
                continue
                
            title = title_match.group(1).strip()
            
            # Skip empty or non-result titles
            if not title or len(title) < 3:
                continue
            
            # Get the href
            href_match = re.search(r'href="([^"]+)"', h2_content)
            if not href_match:
                continue
            
            url = href_match.group(1)
            
            # Decode Bing's redirect URL if needed
            if 'ck/a?' in url and 'u=' in url:
                try:
                    # Extract the encoded URL from the 'u' parameter
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                    encoded_url = parsed.get('u', [''])[0]
                    if encoded_url:
                        url = urllib.parse.unquote(encoded_url)
                except:
                    pass
            
            # Clean title
            title = html_module.unescape(title)
            
            results.append(f"• {title}\n  {url}")
        
        if results:
            return f"Search results:\n\n" + "\n\n".join(results)
        
        return None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (e.g., 'python tutorials', 'latest AI news')",
                }
            },
            "required": ["query"],
        }