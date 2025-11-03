"""
Browser initialization and standard environment configuration
"""

import random
import time
from playwright.sync_api import sync_playwright
import logging

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser initialization with standard browser environment settings"""

    def __init__(self, session_manager, headless=False, block_images=False):
        self.session_manager = session_manager
        self.headless = headless
        self.block_images = block_images
        self.browser = None
        self.context = None
        self.page = None

    def initialize(self, session_data=None):
        """Initialize browser with standard environment configuration"""
        playwright = sync_playwright().start()

        if session_data:
            profile = session_data["profile"]
        else:
            profile = self.session_manager.create_session_profile()

        # Browser selection
        if "Firefox" in profile["user_agent"]:
            browser_type = playwright.firefox
        else:
            browser_type = playwright.chromium

        # Launch with standard browser arguments
        self.browser = browser_type.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                f'--window-size={profile["viewport"]["width"]},{profile["viewport"]["height"]}',
            ],
        )

        # Create context
        context_params = {
            "viewport": profile["viewport"],
            "user_agent": profile["user_agent"],
            "timezone_id": profile["timezone"],
            "locale": profile["locale"],
        }

        if session_data and session_data.get("storage_state"):
            storage_path = session_data["path"] / "storage_state.json"
            if storage_path.exists():
                context_params["storage_state"] = str(storage_path)

        self.context = self.browser.new_context(**context_params)

        if session_data and session_data.get("cookies"):
            self.context.add_cookies(session_data["cookies"])

        self.page = self.context.new_page()

        # Block images if requested
        if self.block_images:
            self._setup_image_blocking()

        self._configure_standard_browser_environment()

        return profile

    def _setup_image_blocking(self):
        """Block image loading for faster page loads"""

        def handle_route(route):
            if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                route.abort()
            else:
                route.continue_()

        self.page.route("**/*", handle_route)
        logger.info("Image blocking enabled (faster loading, less bandwidth)")

    def _configure_standard_browser_environment(self):
        """
        Configure browser to behave like a standard user browser for research purposes.
        
        Sets up realistic browser properties including navigator objects, plugins,
        and permissions to match typical browser behavior patterns.
        """
        browser_config_js = """
        // Configure navigator.webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Configure standard plugins array
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Configure standard language preferences
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Configure Chrome runtime (for Chromium-based browsers)
        window.chrome = {
            runtime: {}
        };
        
        // Configure standard permissions behavior
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Ensure native function appearance
        const originalToString = Function.prototype.toString;
        Function.prototype.toString = function() {
            if (this === window.navigator.permissions.query) {
                return 'function query() { [native code] }';
            }
            return originalToString.call(this);
        };
        """
        self.page.add_init_script(browser_config_js)

    def warm_up_session(self):
        """Warm up session by navigating to Google"""
        logger.info("Warming up session...")
        self.page.goto("https://www.google.com")
        time.sleep(random.uniform(1, 3))

        # Accept cookies if present
        self._handle_cookie_consent()

        # Random mouse movements
        self._random_mouse_movement()
        logger.info("Session warmup complete")

    def _handle_cookie_consent(self):
        """Handle cookie consent dialogs"""
        cookie_buttons = [
            'button:has-text("Accept all")',
            'button:has-text("I agree")',
            'button:has-text("Reject all")',
            'button[id*="accept"]',
            'button[id*="agree"]',
            'div[role="button"]:has-text("Accept")',
        ]

        for button_selector in cookie_buttons:
            try:
                button = self.page.locator(button_selector).first
                if button.is_visible(timeout=2000):
                    button.click()
                    time.sleep(random.uniform(1, 2))
                    return
            except:
                continue

    def _random_mouse_movement(self):
        """Perform random mouse movements"""
        viewport = self.page.viewport_size
        if not viewport:
            return

        for _ in range(random.randint(2, 4)):
            x = random.randint(100, viewport["width"] - 100)
            y = random.randint(100, viewport["height"] - 100)
            self.page.mouse.move(x, y, steps=random.randint(5, 15))
            time.sleep(random.uniform(0.1, 0.3))

    def close(self):
        """Close browser and clean up"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        self.page = None
        self.context = None
        self.browser = None
