from urllib.parse import urlparse
import ipaddress

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from browser.lifecycle import BrowserLifecycle


class BrowserNavigator:
    """Handles browser navigation and URL validation."""

    def __init__(self, lifecycle: BrowserLifecycle):
        self.lifecycle = lifecycle

    def navigate_to(self, url: str, timeout: int = 30000) -> None:
        """Navigate to a URL with protocol validation.

        Args:
            url: URL to navigate to
            timeout: Timeout in milliseconds (default 30000)

        Raises:
            Exception: If URL has unsafe protocol or navigation fails
        """
        if not self._is_safe_url(url):
            raise Exception(
                f"Unsafe URL protocol detected: {url}. "
                "Only http:// and https:// protocols are allowed."
            )

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            self.lifecycle.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            raise Exception(f"Navigation timeout: page took longer than {timeout}ms to load")
        except PlaywrightError as e:
            raise Exception(f"Navigation failed: {str(e)}")

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """Check if URL has a safe protocol and isn't targeting private networks.

        Args:
            url: URL to validate

        Returns:
            True if safe (http/https or no protocol), False otherwise
        """
        url_lower = url.lower().strip()

        if "://" not in url_lower:
            return True

        safe_protocols = ["http://", "https://"]

        dangerous_protocols = [
            "javascript:",
            "data:",
            "file:",
            "ftp:",
            "about:",
            "blob:",
            "vbscript:",
        ]

        for dangerous in dangerous_protocols:
            if url_lower.startswith(dangerous):
                return False

        for safe in safe_protocols:
            if url_lower.startswith(safe):
                try:
                    parsed = urlparse(url)
                    if parsed.hostname:
                        try:
                            ip = ipaddress.ip_address(parsed.hostname)
                            if ip.is_private or ip.is_loopback or ip.is_link_local:
                                return False
                        except ValueError:
                            if parsed.hostname.lower() in ["localhost", "127.0.0.1", "::1"]:
                                return False
                except Exception:
                    pass
                return True

        return False

    def get_current_url(self) -> str:
        """Get the current page URL.

        Returns:
            Current URL as string
        """
        return self.lifecycle.page.url

    def get_title(self) -> str:
        """Get the page title.

        Returns:
            Page title as string
        """
        return self.lifecycle.page.title()
