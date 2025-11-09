import time
from contextlib import contextmanager
from typing import Dict

from agent.coordinator import Coordinator
from agent.context_manager import ContextManager
from agent.subagents.data_reader import DataReader
from agent.subagents.form_filler import FormFiller
from agent.subagents.navigator import Navigator
from browser.controller import BrowserController
from config import Config
from llm.claude_client import ClaudeClient
from utils.logger import logger


def create_subagents(
    claude_client: ClaudeClient,
    browser: BrowserController,
    context_manager: ContextManager,
) -> Dict:
    """Create all sub-agents.

    Args:
        claude_client: Claude API client
        browser: Browser controller
        context_manager: Context manager for page state

    Returns:
        Dict mapping sub-agent names to instances
    """
    return {
        "navigator": Navigator(claude_client, browser, context_manager),
        "form_filler": FormFiller(claude_client, browser, context_manager),
        "data_reader": DataReader(claude_client, browser, context_manager),
    }


@contextmanager
def browser_lifecycle(config: Config):
    """Manage browser lifecycle with automatic cleanup.

    Args:
        config: Application configuration

    Yields:
        BrowserController instance
    """
    browser = BrowserController(config.browser)
    try:
        browser.start()
        logger.info(f"Browser ready! User data: {config.browser.user_data_dir}")
        yield browser
    finally:
        try:
            browser.stop()
        except Exception:
            pass


def get_user_task() -> str:
    """Prompt user for task input.

    Returns:
        User's task description, or empty string if quit
    """
    logger.separator()
    print("\n💬 Enter your task (or 'quit' to exit):")
    print()
    return input("Task: ").strip()


def should_keep_browser_open() -> bool:
    """Ask user if they want to keep browser open.

    Returns:
        True if browser should remain open
    """
    logger.separator()
    print("\n💬 Keep browser open? (yes/no, default: yes)")
    response = input("Your choice: ").strip().lower()
    return response not in ("n", "no")


def wait_for_user_interrupt():
    """Keep program running until user presses Ctrl+C."""
    logger.info("Browser will remain open. Press Ctrl+C when done.")
    print("\n✨ You can continue using the browser manually.")
    print("   When finished, press Ctrl+C to exit.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n\nClosing browser...")


def main() -> None:
    """Main entry point for AutoBrowser."""
    logger.header("🤖 AutoBrowser - Autonomous Web Agent")

    try:
        logger.info("Loading configuration...")
        config = Config.from_env()

        logger.info("Starting browser (WebKit)...")
        with browser_lifecycle(config) as browser:
            context_manager = ContextManager(browser, config.agent.context_token_limit)
            claude_client = ClaudeClient(
                api_key=config.anthropic_api_key,
                model=config.agent.model
            )

            logger.info("Initializing sub-agents...")
            subagents = create_subagents(claude_client, browser, context_manager)

            coordinator = Coordinator(
                claude_client=claude_client,
                browser=browser,
                context_manager=context_manager,
                subagents=subagents,
                config=config.agent,
            )

            task = get_user_task()

            if not task or task.lower() == "quit":
                logger.info("No task provided. Exiting...")
                return

            logger.separator()
            result = coordinator.execute_task(task)

            logger.separator()
            logger.header("📊 Final Summary")
            print(result)

            if should_keep_browser_open():
                wait_for_user_interrupt()
            else:
                logger.info("Closing browser...")

    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user. Shutting down...")
    except Exception as e:
        import anthropic
        if isinstance(e, anthropic.APITimeoutError):
            logger.error("Connection to Claude API timed out. Please check your internet connection and try again.")
        elif isinstance(e, anthropic.APIConnectionError):
            logger.error("Failed to connect to Claude API. Please check your internet connection and try again.")
        elif isinstance(e, anthropic.AuthenticationError):
            logger.error("Authentication failed. Please check your ANTHROPIC_API_KEY in .env file.")
        elif isinstance(e, anthropic.RateLimitError):
            logger.error("Rate limit exceeded. Please wait a moment and try again.")
        elif isinstance(e, anthropic.BadRequestError):
            logger.error(f"API request error: {str(e)}")
            logger.info("This may be due to invalid conversation format. Please report this issue.")
        else:
            logger.error(f"Fatal error: {str(e)}")
            import traceback
            traceback.print_exc()
    finally:
        logger.info("Goodbye! 👋")


if __name__ == "__main__":
    main()
