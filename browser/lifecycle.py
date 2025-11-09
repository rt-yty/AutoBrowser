import platform
import subprocess
from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from config import BrowserConfig


class BrowserLifecycle:
    """Manages browser lifecycle: startup, shutdown, and process management."""

    def __init__(self, config: BrowserConfig):
        self.config = config
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_started: bool = False

    @property
    def page(self) -> Page:
        """Get the current page.

        Returns:
            Current browser page

        Raises:
            RuntimeError: If browser not started
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    @property
    def context(self) -> BrowserContext:
        """Get the browser context.

        Returns:
            Browser context

        Raises:
            RuntimeError: If browser not started
        """
        if not self._context:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._context

    @property
    def is_started(self) -> bool:
        """Check if browser is running."""
        return self._is_started

    def start(self) -> Page:
        """Start the browser with persistent context (saves cookies/sessions).

        Returns:
            The active browser page

        Raises:
            ValueError: If unknown browser type specified
        """
        from utils.logger import logger

        if self._is_started and self._page is not None and self._context is not None:
            logger.info("Browser already running, reusing existing instance")
            return self._page

        logger.info("Starting new browser instance...")

        self.config.user_data_dir.mkdir(parents=True, exist_ok=True)

        self._kill_existing_processes()

        if self._playwright is None:
            self._playwright = sync_playwright().start()
            logger.info("Playwright engine started")

        if self.config.browser_type == "webkit":
            self._context = self._playwright.webkit.launch_persistent_context(
                user_data_dir=str(self.config.user_data_dir),
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )
        elif self.config.browser_type == "chromium":
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.config.user_data_dir),
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )
        elif self.config.browser_type == "firefox":
            self._context = self._playwright.firefox.launch_persistent_context(
                user_data_dir=str(self.config.user_data_dir),
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )
        else:
            raise ValueError(f"Unknown browser type: {self.config.browser_type}")

        self._browser = None

        if len(self._context.pages) > 0:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()

        self._is_started = True
        logger.info(
            f"Browser started successfully (PID: {self._context.pages[0] if self._context.pages else 'unknown'})"
        )

        return self._page

    def stop(self) -> None:
        """Stop the browser and clean up resources (saves session state)."""
        from utils.logger import logger

        if not self._is_started:
            logger.info("Browser not running, nothing to stop")
            return

        logger.info("Stopping browser...")

        if self._context:
            try:
                self._context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping playwright: {e}")

        self._page = None
        self._context = None
        self._playwright = None
        self._is_started = False
        logger.info("Browser stopped successfully")

    def _kill_existing_processes(self) -> None:
        """Kill any existing browser processes using the same user data directory.

        This ensures only one browser instance is running at a time.
        """
        from utils.logger import logger

        try:
            system = platform.system()
            user_data_path = str(self.config.user_data_dir)

            if system == "Darwin":
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", user_data_path],
                        capture_output=True,
                        timeout=5,
                        text=True,
                    )
                    if result.stdout:
                        pids = result.stdout.strip().split("\n")
                        logger.info(f"Found {len(pids)} existing browser processes to kill")
                        for pid in pids:
                            if pid:
                                try:
                                    subprocess.run(["kill", "-9", pid], timeout=2)
                                except Exception:
                                    pass
                except Exception as e:
                    logger.debug(f"Could not kill existing processes: {e}")

            elif system == "Linux":
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", user_data_path],
                        capture_output=True,
                        timeout=5,
                        text=True,
                    )
                    if result.stdout:
                        pids = result.stdout.strip().split("\n")
                        for pid in pids:
                            if pid:
                                subprocess.run(["kill", "-9", pid], timeout=2)
                except Exception:
                    pass

            elif system == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "WebKitWebProcess.exe"],
                    capture_output=True,
                    timeout=5,
                )
                subprocess.run(
                    ["taskkill", "/F", "/IM", "chrome.exe"],
                    capture_output=True,
                    timeout=5,
                )
        except Exception as e:
            logger.debug(f"Process cleanup completed with some errors: {e}")
