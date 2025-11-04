"""
CAPTCHA detection and handling
"""

import time
from typing import Optional, Dict
from datetime import datetime
import logging
from .enums import CAPTCHAType

logger = logging.getLogger(__name__)


class CAPTCHADetector:
    """Detects various types of Google CAPTCHAs and blocks"""

    @staticmethod
    def detect_captcha(page) -> tuple[bool, Optional[CAPTCHAType], Optional[Dict]]:
        """
        Detect if CAPTCHA is present on the page
        Returns: (is_captcha_present, captcha_type, details)
        """

        # Check page content
        page_content = page.content().lower()
        page_url = page.url.lower()

        # Detection patterns
        patterns = {
            CAPTCHAType.RECAPTCHA_V2: [
                'class="g-recaptcha"',
                "data-sitekey",
                "recaptcha/api2",
                "recaptcha__en",
                "recaptcha-checkbox",
                'id="recaptcha"',
            ],
            CAPTCHAType.UNUSUAL_TRAFFIC: [
                "unusual traffic",
                "automated requests",
                "computer network",
                "sorry, your computer or network may be sending automated queries",
            ],
            CAPTCHAType.SUSPICIOUS_ACTIVITY: [
                "suspicious activity",
                "verify you are human",
                "confirm you are not a robot",
            ],
        }

        # Check for each CAPTCHA type
        for captcha_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in page_content:
                    logger.warning(f"CAPTCHA detected: {captcha_type.value}")

                    # Extract additional details
                    details = CAPTCHADetector._extract_captcha_details(page, captcha_type)

                    return True, captcha_type, details

        # Check URL for CAPTCHA/sorry pages
        if "sorry/index" in page_url or "recaptcha" in page_url:
            logger.warning("CAPTCHA page detected in URL")
            return True, CAPTCHAType.UNKNOWN, {"url": page_url}

        # Check for reCAPTCHA iframe (must be visible and blocking)
        try:
            # Check if reCAPTCHA iframe actually exists and is visible
            recaptcha_iframes = page.locator('iframe[src*="recaptcha"]')
            if recaptcha_iframes.count() > 0:
                # Check if it's a visible challenge (not just the invisible badge)
                visible_challenge = page.locator('iframe[src*="recaptcha"][src*="bframe"]')
                if visible_challenge.count() > 0:
                    logger.warning("reCAPTCHA iframe detected")
                    return True, CAPTCHAType.RECAPTCHA_V2, {"has_iframe": True}
        except:
            pass

        # Check if search results are present (inverse check)
        try:
            if "google.com/search" in page_url and "tbm=isch" not in page_url:
                # We're on a search page - check for actual results
                search_div = page.locator("div#search").count()

                result_items = 0

                # Strategy 1: Try stable selectors
                stable_selectors = ["div.g", "div[data-sokoban-container]", "a[jsname]"]
                for selector in stable_selectors:
                    count = page.locator(selector).count()
                    if count > 0:
                        result_items = count
                        break

                # Strategy 2: Dynamic discovery (look for divs with hash-like classes)
                if result_items == 0:
                    # Find divs with 6-char mixed-case class names that contain h3+a
                    all_divs = page.locator("div").all()
                    for div in all_divs[:100]:  # Limit search for performance
                        try:
                            class_attr = div.get_attribute("class")
                            if class_attr:
                                classes = class_attr.split()
                                for cls in classes:
                                    if len(cls) == 6 and cls.isalpha():
                                        if any(c.isupper() for c in cls) and any(
                                            c.islower() for c in cls
                                        ):
                                            # Check if it has result structure
                                            if (
                                                div.locator("h3").count() > 0
                                                and div.locator("a").count() > 0
                                            ):
                                                result_items += 1
                                                break
                        except:
                            continue
                        if result_items > 0:
                            break

                # If search div exists but no result items, might be blocked
                if search_div > 0 and result_items == 0:
                    # Double check it's not just loading
                    time.sleep(1)
                    # Quick recheck with stable selectors
                    for selector in stable_selectors:
                        count = page.locator(selector).count()
                        if count > 0:
                            result_items = count
                            break

                    # Still no results - likely blocked
                    if result_items == 0:
                        logger.warning("No search results found - possible block")
                        return True, CAPTCHAType.UNKNOWN, {"no_results": True}
        except:
            pass

        return False, None, None

    @staticmethod
    def _extract_captcha_details(page, captcha_type) -> Dict:
        """Extract details about the CAPTCHA for solving"""
        details = {
            "type": captcha_type.value,
            "url": page.url,
            "timestamp": datetime.now().isoformat(),
        }

        if captcha_type == CAPTCHAType.RECAPTCHA_V2:
            try:
                # Try to get site key
                sitekey_element = page.locator("[data-sitekey]")
                if sitekey_element.count() > 0:
                    details["sitekey"] = sitekey_element.first.get_attribute("data-sitekey")

                # Check if it's invisible
                details["invisible"] = "invisible" in page.content().lower()

            except Exception as e:
                logger.error(f"Error extracting reCAPTCHA details: {e}")

        elif captcha_type == CAPTCHAType.UNUSUAL_TRAFFIC:
            # Extract any specific message
            try:
                message_element = page.locator('div:has-text("unusual traffic")')
                if message_element.count() > 0:
                    details["message"] = message_element.first.text_content()
            except:
                pass

        return details
