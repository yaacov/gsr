"""
Session management for browser persistence
"""

import random
import json
from datetime import datetime, timedelta
from pathlib import Path


class SessionManager:
    """Manages browser sessions"""

    def __init__(self, session_dir="./sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)

    def create_session_profile(self):
        """Create a unique session profile"""
        session_id = (
            f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        )

        profile = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "search_count": 0,
            "searches": [],
            "user_agent": self._get_random_user_agent(),
            "viewport": {"width": random.randint(1200, 1920), "height": random.randint(800, 1080)},
            "timezone": random.choice(
                ["America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/London"]
            ),
            "locale": random.choice(["en-US", "en-GB", "en-CA"]),
            "typing_speed": random.choice(["fast", "normal", "slow"]),
            "behavior_pattern": random.choice(["casual", "researcher", "quick"]),
        }

        return profile

    def _get_random_user_agent(self):
        """Get random user agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        return random.choice(user_agents)

    def save_session(self, session_data, cookies=None, storage_state=None):
        """Save session data"""
        session_path = self.session_dir / session_data["id"]
        session_path.mkdir(exist_ok=True)

        with open(session_path / "session.json", "w") as f:
            json.dump(session_data, f, indent=2)

        if cookies:
            with open(session_path / "cookies.json", "w") as f:
                json.dump(cookies, f, indent=2)

        if storage_state:
            with open(session_path / "storage_state.json", "w") as f:
                json.dump(storage_state, f, indent=2)

    def load_session(self, session_id=None):
        """Load an existing session"""
        if session_id is None:
            sessions = list(self.session_dir.glob("session_*/session.json"))
            if not sessions:
                return None

            # Get most recent
            sessions_data = []
            for session_file in sessions:
                with open(session_file, "r") as f:
                    data = json.load(f)
                    sessions_data.append((data, session_file.parent))

            sessions_data.sort(key=lambda x: x[0]["last_used"], reverse=True)
            session_data, session_path = sessions_data[0]
        else:
            session_path = self.session_dir / session_id
            if not session_path.exists():
                return None

            with open(session_path / "session.json", "r") as f:
                session_data = json.load(f)

        # Load cookies and storage
        cookies = None
        cookies_file = session_path / "cookies.json"
        if cookies_file.exists():
            with open(cookies_file, "r") as f:
                cookies = json.load(f)

        storage_state = None
        storage_file = session_path / "storage_state.json"
        if storage_file.exists():
            with open(storage_file, "r") as f:
                storage_state = json.load(f)

        return {
            "profile": session_data,
            "cookies": cookies,
            "storage_state": storage_state,
            "path": session_path,
        }

    def should_create_new_session(self, current_session):
        """Determine if new session needed"""
        if not current_session:
            return True

        profile = current_session["profile"]

        if profile["search_count"] >= random.randint(5, 15):
            return True

        last_used = datetime.fromisoformat(profile["last_used"])
        if datetime.now() - last_used > timedelta(hours=random.uniform(1, 4)):
            return True

        return random.random() < 0.1
