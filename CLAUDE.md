# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoBrowser is a minimalist AI agent that controls a real web browser to solve complex multi-step tasks autonomously. It uses Claude (Anthropic) as the decision-making engine and Playwright for browser automation.

**Key Features:**
- Autonomous task execution from natural language descriptions
- No hard-coded behavior - agent analyzes DOM and decides actions dynamically
- Sub-agent architecture for specialized tasks
- Hybrid context management (accessibility tree + HTML drill-down)
- Visible browser with persistent sessions (supports manual login for 2FA)
- Rich terminal logging of all actions and reasoning

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install webkit

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Running the Agent
```bash
# Run the agent
python main.py

# The agent will prompt you for a task, for example:
# "Find Python developer jobs in San Francisco on LinkedIn"
# "Search for the latest MacBook Pro on Apple's website"
```

## Architecture

### High-Level Structure

```
Main Entry (main.py)
    ↓
Coordinator Agent (observe → decide → act → evaluate loop)
    ↓
    ├─→ Direct Actions (click, type, navigate)
    ├─→ Sub-Agents (specialized for specific tasks)
    │   ├─ Navigator (page navigation, menus, links)
    │   ├─ FormFiller (form inputs, dropdowns, submissions)
    │   └─ DataReader (data extraction, tables, lists)
    └─→ Browser Controller (Playwright wrapper)
```

### Core Components

**1. Browser Layer** (`browser/`)
- `controller.py`: Playwright wrapper for browser automation
- `dom_utils.py`: DOM extraction and simplification
  - Uses accessibility tree for semantic overview
  - Extracts HTML snippets for detailed inspection
  - Limits context to ~3000 tokens

**2. Agent Layer** (`agent/`)
- `coordinator.py`: Main agent orchestrator
  - Implements observe-decide-act-evaluate loop
  - Manages conversation with Claude
  - Delegates to sub-agents when appropriate
- `context_manager.py`: Manages page context for the agent
- `tools.py`: Tool registry and definitions
  - Core tools: navigate_to, click, type_text, scroll, wait_for_element
  - Context tools: get_page_overview, get_element_details
  - Meta tools: delegate_to_subagent, task_complete

**3. Sub-Agents** (`agent/subagents/`)
- `base.py`: Base class for all sub-agents
- `navigator.py`: Specialized for navigation tasks
- `form_filler.py`: Specialized for form interactions
- `data_reader.py`: Specialized for data extraction
- Each sub-agent has its own specialized tool set and system prompt

**4. LLM Layer** (`llm/`)
- `claude_client.py`: Anthropic API client with tool calling
- `prompts.py`: System prompts for coordinator and sub-agents
  - Coordinator: High-level orchestration and delegation
  - Navigator: Understanding site structure, finding pages
  - FormFiller: Form field identification and completion
  - DataReader: Structured data extraction

**5. Utils** (`utils/`)
- `logger.py`: Rich terminal logging with emojis and formatting

**6. Configuration** (`config.py`)
- Environment-based configuration
- Browser settings (headless, browser type, viewport)
- Agent settings (max iterations, context token limit, model)

### Agent Loop Design

The coordinator follows this loop:

1. **Observe**: Get current page context
   - Extract accessibility tree
   - Simplify to ~3000 tokens
   - Include URL, title, interactive elements

2. **Decide**: Send context + task to Claude
   - Claude receives system prompt, conversation history, available tools
   - Claude decides: execute tool OR delegate to sub-agent OR complete task

3. **Act**: Execute chosen action
   - If tool: execute via browser controller
   - If delegation: invoke sub-agent with subtask
   - If complete: mark task done

4. **Evaluate**: Process result
   - Update conversation with tool result
   - Provide fresh context if page changed
   - Log reasoning and outcomes
   - Repeat until task complete or max iterations

### Context Management Strategy

**Hybrid Approach:**
- **Primary**: Accessibility tree provides semantic overview
  - Extracts roles: button, link, textbox, heading, etc.
  - Groups by type, limits to first 10 of each
  - ~500-2000 tokens typically

- **Secondary**: HTML drill-down for specifics
  - Agent can request detailed HTML via `get_element_details(selector)`
  - HTML is simplified: scripts/styles removed
  - Used when accessibility tree lacks necessary detail

**Token Budget:**
- Max ~3000 tokens per context update (configurable)
- Truncation preserves structure (keeps headings, critical elements)
- Progressive disclosure: start broad, drill down as needed

### Sub-Agent Architecture

**Why Sub-Agents:**
- Specialization improves success rate
- Focused tool sets reduce confusion
- Specialized prompts provide domain expertise
- Coordinator delegates instead of doing everything

**Communication Flow:**
```
User Task → Coordinator
  ↓
Coordinator analyzes → "This is a navigation task"
  ↓
Delegate to Navigator → Navigator executes subtask
  ↓
Navigator returns result → Coordinator continues
```

**Sub-Agent Execution:**
- Each sub-agent runs its own observe-decide-act loop
- Limited to 10 steps by default (prevents infinite loops)
- Returns result summary to coordinator
- Maintains own conversation history (isolated from coordinator)

### Tool System

Tools are the interface between LLM decisions and browser actions.

**Tool Definition:**
```python
Tool(
    name="click",
    description="Click on an element",
    parameters={
        "selector": {"type": "string", "description": "CSS selector"},
        "description": {"type": "string", "description": "Element description"}
    },
    handler=lambda selector, description: click_handler(...)
)
```

**Tool Execution Flow:**
1. Claude returns tool call with name + arguments
2. ToolRegistry looks up tool by name
3. Handler function executes with arguments
4. Result (string) returned to Claude in next message

**Available Tools by Agent:**
- **Coordinator**: All tools (navigation, interaction, context, delegation, completion)
- **Navigator**: Navigation subset (navigate_to, click, scroll, context)
- **FormFiller**: Form subset (type_text, click, context)
- **DataReader**: Read-only subset (context tools, scroll)

## Key Patterns and Conventions

### Type Hints
All functions use Python type hints for clarity and IDE support.

### Error Handling
- Tool handlers catch exceptions and return error strings
- Agent receives errors as tool results and can adjust strategy
- No crashes - always graceful failure with explanation

### Logging
- Every action logged with rich formatting
- Color-coded by success/failure
- Shows: agent name, tool name, arguments, reasoning, result
- Emojis for visual clarity (🤖 Coordinator, 🧭 Navigator, etc.)

### Conversation Management
- Each agent maintains MessageParam list
- User messages contain task/context
- Assistant messages contain text reasoning + tool calls
- Tool results sent back as user messages with tool_result type

### Immutability
- Configuration is immutable (dataclasses)
- Browser state modified only via explicit tools
- No hidden side effects

## CRITICAL: Behavior Rules

The agent implements strict behavior rules to ensure safe, efficient operation. See `BEHAVIOR_RULES.md` for full details.

### 1. HTML and Context Management

**NEVER output full raw HTML:**
- All system prompts enforce this rule
- Agent must summarize tool results in 1-3 bullet points
- Use narrow selectors (e.g., '.search-form'), NEVER 'body' or 'html'
- `get_element_details()` enforces 2000 character limit
- HTML is aggressively simplified (no scripts, styles, data attributes)
- Context manager logs warnings when truncation occurs

**Why:** Prevents console flooding, stays within token limits, improves debugging.

### 2. Security and Human Intervention

**Agent MUST NOT bypass security mechanisms:**
- Detects: CAPTCHA, login forms, 2FA, human verification
- When detected: immediately calls `request_human_help()`
- Execution pauses with clear user instructions
- User completes action manually in browser
- After Enter pressed: agent refreshes context and continues
- Never attempts to automate login/CAPTCHA/2FA

**Detection signals:**
- Keywords: "CAPTCHA", "SmartCaptcha", "Я не робот", "I am not a robot"
- Keywords: "two-factor", "2FA", "verification code", "authenticate"
- Login forms with password fields

**Implementation:**
- `request_human_help(description)` tool in coordinator (`agent/tools.py:221-234`)
- Pause/resume logic in coordinator (`agent/coordinator.py:115-138, 174-197`)
- Security rules in all system prompts (`llm/prompts.py:64-91`)

**Flow example:**
```
Agent detects CAPTCHA
→ Calls request_human_help("Please solve the CAPTCHA")
→ Terminal shows: "⏸️ PAUSED - Human Action Required"
→ User solves CAPTCHA, presses Enter
→ Agent gets fresh page context
→ Agent continues with task
```

**Why:** Respects security, prevents infinite loops, enables persistent sessions with manual login.

## Dependencies

**Core:**
- `anthropic`: Claude API client
- `playwright`: Browser automation
- `pydantic`: Data validation
- `rich`: Terminal UI
- `python-dotenv`: Environment configuration

**Python Version:** 3.12+

## Project Constraints

1. **No hard-coded behavior**: Agent must analyze and decide dynamically
2. **Visible browser only**: Never headless (requirement for persistent sessions)
3. **Token limits**: Context must fit in ~3000 tokens
4. **Minimal dependencies**: No LangChain, LlamaIndex, CrewAI
5. **Clean, typed code**: Strong type hints, explicit data structures

## Future Enhancements

Potential improvements (not yet implemented):
- Error recovery with retry strategies
- Security layer for destructive actions (needs user confirmation)
- Multi-page workflows with state persistence
- Screenshot analysis for visual understanding
- Session state saving/loading
- Parallel action execution
- More sophisticated selector generation
- Better failure diagnostics
