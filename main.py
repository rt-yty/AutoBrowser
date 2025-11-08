"""AutoBrowser - Autonomous web browsing agent."""

import sys
from typing import Dict

from agent.coordinator import Coordinator
from agent.context_manager import ContextManager
from agent.subagents.navigator import Navigator
from agent.subagents.form_filler import FormFiller
from agent.subagents.data_reader import DataReader
from browser.controller import BrowserController
from config import Config
from llm.claude_client import ClaudeClient
from utils.logger import logger


def create_subagents(
    claude_client: ClaudeClient, browser: BrowserController, context_manager: ContextManager
) -> Dict:
    """Create all sub-agents."""
    return {
        "navigator": Navigator(claude_client, browser, context_manager),
        "form_filler": FormFiller(claude_client, browser, context_manager),
        "data_reader": DataReader(claude_client, browser, context_manager),
    }


def main() -> None:
    """Main entry point for AutoBrowser."""
    try:
        # Load configuration
        logger.header("🤖 AutoBrowser - Autonomous Web Agent")
        logger.info("Loading configuration...")
        config = Config.from_env()

        # Initialize browser
        logger.info("Starting browser (WebKit)...")
        browser = BrowserController(config.browser)
        page = browser.start()
        logger.info(f"Browser ready! User data: {config.browser.user_data_dir}")

        # Initialize context manager
        context_manager = ContextManager(browser, config.agent.context_token_limit)

        # Initialize Claude client
        claude_client = ClaudeClient(
            api_key=config.anthropic_api_key, model=config.agent.model
        )

        # Create sub-agents
        logger.info("Initializing sub-agents...")
        subagents = create_subagents(claude_client, browser, context_manager)

        # Create coordinator
        coordinator = Coordinator(
            claude_client=claude_client,
            browser=browser,
            context_manager=context_manager,
            subagents=subagents,
            config=config.agent,
        )

        # Get task from user
        logger.separator()
        print("\n💬 Enter your task (or 'quit' to exit):")
        print("Example: Find Python developer jobs in San Francisco on LinkedIn")
        print()
        task = input("Task: ").strip()

        if not task or task.lower() == "quit":
            logger.info("No task provided. Exiting...")
            browser.stop()
            return

        # Execute task
        logger.separator()
        result = coordinator.execute_task(task)

        # Show final summary
        logger.separator()
        logger.header("📊 Final Summary")
        print(result)

        # Ask if user wants to keep browser open
        logger.separator()
        print("\n💬 Keep browser open? (yes/no, default: yes)")
        keep_open = input("Your choice: ").strip().lower()

        if keep_open in ['n', 'no']:
            logger.info("Closing browser...")
            browser.stop()
        else:
            logger.info("Browser will remain open. Press Ctrl+C when done.")
            print("\n✨ You can continue using the browser manually.")
            print("   When finished, press Ctrl+C to exit.\n")
            try:
                # Keep program running until user interrupts
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\n\nClosing browser...")
                browser.stop()

    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user. Shutting down...")
        try:
            browser.stop()
        except:
            pass
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            browser.stop()
        except:
            pass
    finally:
        logger.info("Goodbye! 👋")


if __name__ == "__main__":
    main()
