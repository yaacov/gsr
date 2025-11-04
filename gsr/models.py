"""
Data models for search results
"""

from typing import List, Dict
from datetime import datetime
from .enums import SearchStatus


class SearchResult:
    """Container for search results with status information"""

    def __init__(
        self,
        status: SearchStatus,
        results: List = None,
        captcha_info: Dict = None,
        error: str = None,
    ):
        self.status = status
        self.results = results or []
        self.captcha_info = captcha_info
        self.error = error
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "status": self.status.value,
            "results": self.results,
            "captcha_info": self.captcha_info,
            "error": self.error,
            "timestamp": self.timestamp,
        }
