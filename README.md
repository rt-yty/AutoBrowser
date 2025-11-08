# AutoBrowser 🤖

An autonomous AI agent that controls a real web browser to solve complex multi-step tasks using natural language.

## Features

- **Fully Autonomous**: Give it a task in plain English, and it figures out how to accomplish it
- **No Hard-Coding**: The agent analyzes websites dynamically—no pre-programmed scenarios
- **Sub-Agent Architecture**: Specialized agents for navigation, forms, and data extraction
- **Smart Context Management**: Uses accessibility tree + HTML drill-down to stay within token limits
- **Persistent Sessions**: Visible browser that supports manual login for 2FA and other authentication
- **Rich Logging**: Beautiful terminal output showing every action and reasoning

## Example Tasks

```
"Find Python developer jobs in San Francisco on LinkedIn"
"Search for the latest MacBook Pro on Apple's website and tell me the price"
"Go to GitHub and find repositories about browser automation"
```

## Quick Start

### Prerequisites

- Python 3.12+
- Anthropic API key ([get one here](https://console.anthropic.com/))

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd AutoBrowser

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install webkit

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Running

```bash
python main.py
```

Enter your task when prompted, and watch the agent work!

## Architecture

```
┌─────────────────────────────────────┐
│         User Task (CLI)             │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│      Coordinator Agent              │
│   (observe → decide → act → eval)   │
└───────┬─────────────────────────────┘
        │
        ├──→ Direct Browser Actions
        │    (click, type, navigate)
        │
        ├──→ Navigator Sub-Agent
        │    (find pages, menus, links)
        │
        ├──→ FormFiller Sub-Agent
        │    (fill forms, submit data)
        │
        └──→ DataReader Sub-Agent
             (extract tables, lists, content)
```

### Key Components

- **Browser Controller**: Playwright wrapper for automation
- **Context Manager**: Extracts and simplifies page content
- **Coordinator**: Main agent with observe-decide-act loop
- **Sub-Agents**: Specialized agents for specific task types
- **Tool System**: Bridge between AI decisions and browser actions
- **Claude Client**: Anthropic API with tool calling support

## How It Works

1. **Observe**: Agent gets page context via accessibility tree
2. **Decide**: Claude analyzes context and chooses actions
3. **Act**: Execute browser actions or delegate to sub-agents
4. **Evaluate**: Check results and decide next step
5. **Repeat**: Continue until task is complete

The agent sees the page through its accessibility tree (semantic structure) and can drill down into specific elements when needed. All context is kept under ~3000 tokens to fit in Claude's context window.

## Project Structure

```
autobrowser/
├── main.py                   # Entry point
├── config.py                 # Configuration management
├── agent/
│   ├── coordinator.py        # Main orchestrator
│   ├── context_manager.py    # Page context extraction
│   ├── tools.py             # Tool definitions
│   └── subagents/           # Specialized sub-agents
├── browser/
│   ├── controller.py        # Playwright wrapper
│   └── dom_utils.py         # DOM extraction
├── llm/
│   ├── claude_client.py     # Anthropic API client
│   └── prompts.py           # System prompts
└── utils/
    └── logger.py            # Rich terminal logging
```

## Configuration

Edit `.env` to configure:

```bash
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional
BROWSER_TYPE=webkit          # webkit, chromium, or firefox
MAX_ITERATIONS=50            # Max steps before timeout
CONTEXT_TOKEN_LIMIT=3000     # Token budget for page context
```

## Design Principles

1. **Simplicity**: Minimal dependencies, clean architecture
2. **Explainability**: Every action is logged with reasoning
3. **Robustness**: Graceful error handling, no crashes
4. **Flexibility**: Works on any website without hard-coding
5. **Efficiency**: Smart context management for token limits

## Limitations

- Single-task execution (exits after completion)
- No error recovery/retry logic yet
- No security confirmations for destructive actions
- Limited to sequential actions (no parallelization)

## Future Improvements

- Multi-turn interactive sessions
- Error recovery with alternative strategies
- Security layer for dangerous actions
- Screenshot analysis for visual understanding
- State persistence across sessions
- Parallel action execution

## Contributing

This is a minimal MVP. Contributions welcome for:
- Better selector generation strategies
- More robust error handling
- Additional sub-agent types
- Performance optimizations
- Test coverage

## License

MIT

## Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/) for AI capabilities
- [Playwright](https://playwright.dev/) for browser automation
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
