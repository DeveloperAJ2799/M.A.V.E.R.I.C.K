"""Fetch URL tool - get web page content."""
import requests
import re
from typing import Any, Dict
from .base import Tool, ToolResult


class FetchUrlTool(Tool):
    """Tool for fetching and extracting content from web pages."""

    def __init__(self):
        super().__init__(
            name="fetch_url",
            description="Fetch a web page and extract its text content. Input: JSON with 'url' and optional 'max_chars'.",
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def execute(self, **kwargs) -> ToolResult:
        url = kwargs.get("url", "")
        max_chars = kwargs.get("max_chars", 5000)
        
        if not url:
            return ToolResult(success=False, result=None, error="No URL provided")
        
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                content = self._extract_text(response.text, max_chars)
                title = self._extract_title(response.text)
                
                result = f"Page: {title}\nURL: {response.url}\n\n{content}"
                return ToolResult(success=True, result=result)
            else:
                return ToolResult(success=False, result=None, error=f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            return ToolResult(success=False, result=None, error="Request timed out")
        except requests.exceptions.RequestException as e:
            return ToolResult(success=False, result=None, error=f"Request failed: {str(e)}")

    def _extract_title(self, html: str) -> str:
        """Extract page title."""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
        if title_match:
            return re.sub(r'\s+', ' ', title_match.group(1)).strip()
        return "Untitled"

    def _extract_text(self, html: str, max_chars: int) -> str:
        """Extract clean text from HTML."""
        
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # Replace common block elements with newlines
        html = re.sub(r'</(p|div|li|tr|h[1-6])>', '\n', html, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Clean up whitespace
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        # Limit length
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        return text

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL to fetch (e.g., https://example.com/article)",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return (default: 5000)",
                }
            },
            "required": ["url"],
        }