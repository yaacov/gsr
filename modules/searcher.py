"""
Human-like Google search implementation for research purposes
"""

import random
import time
from datetime import datetime, timedelta
from typing import Optional, Callable
import logging

from .enums import SearchStatus, CAPTCHAType
from .models import SearchResult
from .captcha import CAPTCHADetector
from .session import SessionManager
from .browser import BrowserManager

logger = logging.getLogger(__name__)


class HumanLikeGoogleSearcher:
    """Enhanced Google searcher with CAPTCHA detection and handling"""

    def __init__(
        self,
        captcha_callback: Optional[Callable] = None,
        auto_retry_on_captcha: bool = False,
        max_retries: int = 3,
        headless: bool = False,
        typing_style: str = "normal",
        session_id: Optional[str] = None,
        block_images: bool = False,
    ):
        """
        Initialize searcher with CAPTCHA handling options

        Args:
            captcha_callback: Function to call when CAPTCHA detected
            auto_retry_on_captcha: Whether to retry on CAPTCHA
            max_retries: Maximum retry attempts
            headless: Run browser in headless mode (no window)
            typing_style: Typing speed ('fast', 'normal', 'slow')
            session_id: Force specific session ID (None = auto)
            block_images: Block image loading (faster, less bandwidth)
        """
        self.session_manager = SessionManager()
        self.captcha_detector = CAPTCHADetector()
        self.browser_manager = None
        self.current_session = None
        self.forced_session_id = session_id
        self.headless = headless
        self.default_typing_style = typing_style
        self.block_images = block_images

        # CAPTCHA handling
        self.captcha_callback = captcha_callback
        self.auto_retry_on_captcha = auto_retry_on_captcha
        self.max_retries = max_retries
        self.captcha_count = 0
        self.last_captcha_time = None

        # Statistics
        self.stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "captcha_encounters": 0,
            "blocks": 0,
            "errors": 0,
        }

        self.typing_patterns = {
            "fast": (5, 40),
            "normal": (30, 110),
            "slow": (100, 250),
        }

    def search(self, query: str, reuse_session: bool = True, retry_count: int = 0) -> SearchResult:
        """Perform a search with CAPTCHA detection"""
        try:
            logger.info(f"Searching for: {query}")

            # Initialize browser if needed
            if not self.browser_manager or not self.browser_manager.page:
                self._initialize_or_reuse_session(reuse_session)

            page = self.browser_manager.page

            # Navigate to Google if needed
            if "google.com" not in page.url:
                page.goto("https://www.google.com")
                time.sleep(random.uniform(1, 2))

            # Check for CAPTCHA
            is_captcha, captcha_type, details = self.captcha_detector.detect_captcha(page)
            if is_captcha:
                return self._handle_captcha(captcha_type, details, query, retry_count)

            # Perform search
            self._perform_search_actions(query)

            # Check for CAPTCHA after search
            is_captcha, captcha_type, details = self.captcha_detector.detect_captcha(page)
            if is_captcha:
                return self._handle_captcha(captcha_type, details, query, retry_count)

            # Extract results
            results = self._extract_results()

            # Update statistics
            self.stats["total_searches"] += 1
            self.stats["successful_searches"] += 1

            # Update session
            if self.current_session:
                self.current_session["profile"]["search_count"] += 1
                self.current_session["profile"]["last_used"] = datetime.now().isoformat()
                self._save_current_session()

            return SearchResult(status=SearchStatus.SUCCESS, results=results)

        except Exception as e:
            logger.error(f"Search error: {e}")
            self.stats["errors"] += 1
            return SearchResult(status=SearchStatus.ERROR, error=str(e))

    def _handle_captcha(
        self, captcha_type: CAPTCHAType, details: dict, query: str, retry_count: int
    ) -> SearchResult:
        """Handle CAPTCHA detection"""
        logger.warning(f"CAPTCHA encountered: {captcha_type.value}")
        self.captcha_count += 1
        self.last_captcha_time = datetime.now()
        self.stats["captcha_encounters"] += 1

        captcha_info = {
            "type": captcha_type.value,
            "details": details,
            "encounter_count": self.captcha_count,
            "session_id": self.current_session["profile"]["id"] if self.current_session else None,
        }

        # Check if it's a hard block
        if captcha_type == CAPTCHAType.UNUSUAL_TRAFFIC:
            self.stats["blocks"] += 1
            self._close_browser()
            self.current_session = None
            return SearchResult(
                status=SearchStatus.BLOCKED,
                captcha_info=captcha_info,
                error="Blocked by Google - unusual traffic detected",
            )

        # Try callback if provided
        if self.captcha_callback:
            try:
                solution = self.captcha_callback(captcha_type, details, self.browser_manager.page)
                if solution:
                    return self.search(query, reuse_session=True, retry_count=retry_count)
            except Exception as e:
                logger.error(f"CAPTCHA callback error: {e}")

        # Auto-retry with new session if configured
        if self.auto_retry_on_captcha and retry_count < self.max_retries:
            wait_time = min(30 * (retry_count + 1), 120)
            logger.info(f"Auto-retry {retry_count + 1}/{self.max_retries} after {wait_time}s")
            time.sleep(wait_time)

            self._close_browser()
            self.current_session = None
            return self.search(query, reuse_session=False, retry_count=retry_count + 1)

        return SearchResult(status=SearchStatus.CAPTCHA_DETECTED, captcha_info=captcha_info)

    def _initialize_or_reuse_session(self, reuse_session: bool):
        """Initialize or reuse browser session"""
        # If forced session ID is specified, load it
        if self.forced_session_id:
            self.current_session = self.session_manager.load_session(self.forced_session_id)
            if self.current_session:
                logger.info(f"Using forced session: {self.forced_session_id}")
                self.browser_manager = BrowserManager(
                    self.session_manager, self.headless, self.block_images
                )
                self.browser_manager.initialize(self.current_session)
                self.browser_manager.warm_up_session()
                return
            else:
                logger.warning(f"Forced session '{self.forced_session_id}' not found, creating new")
                reuse_session = False

        # Check if we should create new session due to recent CAPTCHA
        if self.last_captcha_time:
            time_since_captcha = datetime.now() - self.last_captcha_time
            if time_since_captcha < timedelta(minutes=5):
                reuse_session = False

        # Decide whether to use existing session or create new one
        if reuse_session and self.current_session:
            if not self.session_manager.should_create_new_session(self.current_session):
                return
            else:
                self._close_browser()
                self.current_session = None

        # Load or create session
        if self.current_session is None:
            if reuse_session:
                self.current_session = self.session_manager.load_session()

                if self.current_session:
                    logger.info(f"Loaded session: {self.current_session['profile']['id']}")
                    self.browser_manager = BrowserManager(
                        self.session_manager, self.headless, self.block_images
                    )
                    self.browser_manager.initialize(self.current_session)
                    self.browser_manager.warm_up_session()
                    return

            # Create new session
            self.browser_manager = BrowserManager(self.session_manager, self.headless)
            profile = self.browser_manager.initialize()
            self.current_session = {
                "profile": profile,
                "cookies": None,
                "storage_state": None,
                "path": self.session_manager.session_dir / profile["id"],
            }
            logger.info(f"Created session: {profile['id']}")
            self.browser_manager.warm_up_session()

    def _perform_search_actions(self, query):
        """Perform the actual search with human-like behavior"""
        page = self.browser_manager.page

        # Find search box
        search_box = None
        selectors = [
            'textarea[name="q"]',
            'input[name="q"]',
            'textarea[title*="Search"]',
            'input[title*="Search"]',
        ]

        for selector in selectors:
            try:
                search_box = page.locator(selector)
                if search_box.count() > 0:
                    break
            except:
                continue

        if not search_box or search_box.count() == 0:
            raise Exception("Search box not found")

        # Click search box
        search_box.click(position={"x": random.randint(10, 50), "y": random.randint(5, 15)})
        time.sleep(random.uniform(0.3, 0.8))

        # Clear and type query
        search_box.clear()
        # Use default_typing_style if set, otherwise use session profile
        typing_speed = self.default_typing_style
        if not typing_speed and self.current_session:
            typing_speed = self.current_session["profile"].get("typing_speed", "normal")
        self._type_with_personality(search_box, query, typing_speed or "normal")

        # Submit
        time.sleep(random.uniform(0.5, 1.5))
        search_box.press("Enter")

        # Wait for results
        try:
            page.wait_for_selector("div#search", timeout=10000)
        except:
            pass

        time.sleep(random.uniform(1, 2))

    def _type_with_personality(self, element, text, typing_speed="normal"):
        """Type with human-like patterns"""
        pattern = self.typing_patterns.get(typing_speed, self.typing_patterns["normal"])
        for char in text:
            element.type(char, delay=random.randint(*pattern))
            if random.random() < 0.05:
                time.sleep(random.uniform(0.5, 1.5))

    def _discover_result_containers(self, page):
        """Dynamically discover result containers by structure, not hardcoded classes"""
        try:
            # Look for divs that contain the structure of a search result (h3 + link)
            # This is more resilient than hardcoded class names
            containers = page.query_selector_all("div")

            result_containers = []
            for container in containers:
                # Check if this div looks like a result container
                try:
                    # Must have: h3 (title) and a (link)
                    has_title = container.query_selector("h3") is not None
                    has_link = container.query_selector("a") is not None

                    if has_title and has_link:
                        # Check if class name looks like a hash (6 chars, mixed case)
                        class_attr = container.get_attribute("class")
                        if class_attr:
                            classes = class_attr.split()
                            for cls in classes:
                                # Hash pattern: 6 chars, contains both upper and lower
                                if len(cls) == 6 and cls.isalpha():
                                    if any(c.isupper() for c in cls) and any(
                                        c.islower() for c in cls
                                    ):
                                        result_containers.append(container)
                                        break
                except:
                    continue

            return result_containers
        except:
            return []

    def _extract_results(self):
        """Extract search results"""
        results = []
        page = self.browser_manager.page

        try:
            # Strategy 1: Try known stable selectors first
            stable_selectors = [
                "div.g",  # Classic (stable)
                "div[data-sokoban-container]",  # Attribute-based (stable)
            ]

            result_elements = []
            for selector in stable_selectors:
                result_elements = page.query_selector_all(selector)
                if result_elements:
                    logger.info(f"Found results using stable selector: {selector}")
                    break

            # Strategy 2: If stable selectors fail, discover containers dynamically
            if not result_elements:
                logger.info("Stable selectors failed, discovering containers dynamically...")
                result_elements = self._discover_result_containers(page)
                if result_elements:
                    logger.info(f"Discovered {len(result_elements)} result containers by structure")

            # Strategy 3: Last resort - try current known working selector
            if not result_elements:
                result_elements = page.query_selector_all("div.MjjYud")
                if result_elements:
                    logger.info("Found results using known working selector: div.MjjYud")

            if not result_elements:
                logger.warning("No result containers found using any strategy")
                return results

            for element in result_elements[:10]:
                try:
                    title_elem = element.query_selector("h3")
                    link_elem = element.query_selector("a")
                    # Try multiple snippet selectors (Google changes these frequently)
                    snippet_elem = element.query_selector(
                        "div[data-content-feature], div.VwiC3b, div[data-sncf], span"
                    )

                    if title_elem and link_elem:
                        results.append(
                            {
                                "title": title_elem.text_content(),
                                "url": link_elem.get_attribute("href"),
                                "snippet": snippet_elem.text_content() if snippet_elem else None,
                            }
                        )
                except:
                    continue

            logger.info(f"Extracted {len(results)} results")

        except Exception as e:
            logger.error(f"Error extracting results: {e}")

        return results

    def _save_current_session(self):
        """Save session state"""
        if not self.current_session or not self.browser_manager.context:
            return

        try:
            cookies = self.browser_manager.context.cookies()
            storage_state = self.browser_manager.context.storage_state()

            self.session_manager.save_session(
                self.current_session["profile"], cookies, storage_state
            )
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def _close_browser(self):
        """Close browser and clean up"""
        if self.browser_manager:
            self._save_current_session()
            self.browser_manager.close()
            self.browser_manager = None

    def get_statistics(self):
        """Get search statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_searches"] / self.stats["total_searches"]
                if self.stats["total_searches"] > 0
                else 0
            ),
            "captcha_rate": (
                self.stats["captcha_encounters"] / self.stats["total_searches"]
                if self.stats["total_searches"] > 0
                else 0
            ),
            "current_session": (
                self.current_session["profile"]["id"] if self.current_session else None
            ),
            "last_captcha": self.last_captcha_time.isoformat() if self.last_captcha_time else None,
        }

    def close(self):
        """Clean shutdown"""
        self._close_browser()
        logger.info(f"Final statistics: {self.get_statistics()}")
