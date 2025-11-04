"""
Enumeration types for search status and CAPTCHA detection
"""

from enum import Enum


class SearchStatus(Enum):
    """Status codes for search results"""

    SUCCESS = "success"
    CAPTCHA_DETECTED = "captcha_detected"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    TIMEOUT = "timeout"


class CAPTCHAType(Enum):
    """Types of CAPTCHAs/blocks Google uses"""

    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    UNUSUAL_TRAFFIC = "unusual_traffic"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    UNKNOWN = "unknown"
