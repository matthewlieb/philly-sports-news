"""Tavily web search (optional: returns [] when TAVILY_API_KEY is unset or the call fails)."""
import os
import sys


def tavily_search(query: str, topic: str = "news", max_results: int = 8, time_range: str | None = None) -> list[dict]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []
    try:
        from tavily import TavilyClient
        kwargs = {"query": query, "topic": topic, "search_depth": "basic", "max_results": max_results}
        if time_range:
            kwargs["time_range"] = time_range
        return list(TavilyClient(api_key=api_key).search(**kwargs).get("results") or [])
    except Exception as e:
        print(f"Tavily search failed: {e}", file=sys.stderr)
        return []
