"""Configuration management for AutoBrowser."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class BrowserConfig:
    """Browser configuration."""

    headless: bool = False
    browser_type: str = "webkit"
    viewport_width: int = 1280
    viewport_height: int = 720
    user_data_dir: Path = Path.home() / ".autobrowser" / "browser_data"


@dataclass
class AgentConfig:
    """Agent configuration."""

    max_iterations: int = 50
    context_token_limit: int = 3000
    model: str = "claude-sonnet-4-20250514"


@dataclass
class Config:
    """Main configuration."""

    anthropic_api_key: str
    browser: BrowserConfig
    agent: AgentConfig

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Please create a .env file or set the environment variable."
            )

        browser = BrowserConfig(
            headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
            browser_type=os.getenv("BROWSER_TYPE", "webkit"),
        )

        agent = AgentConfig(
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50")),
            context_token_limit=int(os.getenv("CONTEXT_TOKEN_LIMIT", "3000")),
        )

        return cls(
            anthropic_api_key=api_key,
            browser=browser,
            agent=agent,
        )
