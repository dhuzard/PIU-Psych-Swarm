"""
config.py — Configuration Engine for the Research Swarm

Loads swarm_config.yml and dynamically builds:
  - System prompts (from Jinja2 templates + persona files)
  - Reviewer-2 prompts (from banned_words, required_elements, tone)
  - Tool registries (from module + function references)
  - LLM model instances (from provider + model name)

A user should NEVER need to edit this file. All customization flows
through swarm_config.yml and agents/*/persona.md files.
"""

import os
import importlib
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template
from rich.console import Console

console = Console()

# Resolve the project root (one level above automation/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "swarm_config.yml"


# ── Default System Prompt Template ───────────────────
# Used if no system_prompt_template key exists in the config.
DEFAULT_TEMPLATE = """\
You are the {{ swarm.name }}, an orchestration of specialist agents:
{%- for p in personas %}
- {{ p.icon }} **{{ p.name }}** ({{ p.role }})
{%- endfor %}

CRITICAL DIRECTIVE: After every search, you MUST call the traceability tool
to log findings using epistemic tags: {{ epistemic_tags | join(', ') }}.

FORMATTING: Include formal in-text citations and a complete Reference section.

Use your tools to fulfill the user request precisely.
"""


def load_config(config_path: Path = CONFIG_PATH) -> dict:
    """Load and validate the swarm configuration from YAML."""
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create a swarm_config.yml in the project root.\n"
            f"See QUICKSTART.md for instructions."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Validate required top-level keys
    required_keys = ["swarm", "model", "personas", "tools", "reviewer"]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(
            f"swarm_config.yml is missing required keys: {missing}\n"
            f"Please refer to the example configuration."
        )

    return config


def load_persona_content(persona_file: str) -> str:
    """Read a persona markdown file from disk.

    Resolves paths relative to the project root.
    """
    path = PROJECT_ROOT / persona_file
    if not path.exists():
        console.print(f"[yellow]Warning: Persona file not found: {path}[/yellow]")
        return ""
    return path.read_text(encoding="utf-8")


def build_system_prompt(config: dict) -> str:
    """Assemble the system prompt from config + persona files via Jinja2."""
    # Enrich persona dicts with their loaded file contents
    personas_with_content = []
    for p in config["personas"]:
        p_copy = dict(p)
        p_copy["content"] = load_persona_content(p.get("persona_file", ""))
        personas_with_content.append(p_copy)

    # Render the Jinja2 template
    template_str = config.get("system_prompt_template", DEFAULT_TEMPLATE)
    template = Template(template_str)

    return template.render(
        swarm=config["swarm"],
        personas=personas_with_content,
        tools=config["tools"],
        epistemic_tags=config.get("epistemic_tags", ["[FACT]", "[INFERENCE]"]),
        reviewer=config["reviewer"],
    )


def build_reviewer_prompt(config: dict) -> str:
    """Dynamically construct the Reviewer-2 prompt from config.

    If the config provides a `custom_prompt`, that is used verbatim.
    Otherwise, the prompt is assembled from `banned_words`,
    `required_elements`, and `tone`.
    """
    r = config["reviewer"]

    # Allow full override
    if "custom_prompt" in r and r["custom_prompt"]:
        return r["custom_prompt"]

    banned = ", ".join(f"'{w}'" for w in r.get("banned_words", []))
    required = " AND ".join(r.get("required_elements", []))
    tone = r.get("tone", "objective and neutral")

    return (
        f"You are Reviewer-2 (Adversarial Critic). You read the agent's final text output. "
        f"If they use hype words ({banned}), OR if they fail to maintain a {tone} tone, "
        f"you MUST reject it. Additionally, if the text does NOT include {required}, "
        f"you MUST reject it. To reject, reply starting exactly with 'REJECTED: ' and list the "
        f"exact flaws prohibiting publication. "
        f"If it is perfectly factual, properly cited, and contains all required elements, "
        f"reply exactly with 'APPROVED'."
    )


def load_tools(config: dict) -> list:
    """Dynamically import and return tool functions from config.

    Each tool entry in swarm_config.yml maps a logical name to:
      module: "automation.tools"
      function: "search_pubmed"

    This function imports the module and retrieves the decorated @tool function.
    """
    tool_functions = []
    seen = set()

    for tool_name, tool_spec in config["tools"].items():
        module_path = tool_spec["module"]
        function_name = tool_spec["function"]
        key = f"{module_path}.{function_name}"

        # Avoid duplicates (multiple personas may reference the same tool)
        if key in seen:
            continue
        seen.add(key)

        try:
            module = importlib.import_module(module_path)
            func = getattr(module, function_name)
            tool_functions.append(func)
        except (ModuleNotFoundError, AttributeError) as e:
            console.print(
                f"[red]Error loading tool '{tool_name}' "
                f"({module_path}.{function_name}): {e}[/red]"
            )
            console.print(
                f"[yellow]Skipping tool '{tool_name}'. "
                f"The swarm will run without it.[/yellow]"
            )

    if not tool_functions:
        raise ValueError(
            "No tools could be loaded from swarm_config.yml. "
            "Check that the module paths and function names are correct."
        )

    return tool_functions


def create_model(config: dict) -> Any:
    """Create an LLM instance from the config's model specification.

    Supports multiple providers: openai, anthropic, google.
    """
    provider = config["model"].get("provider", "openai")
    model_name = config["model"]["name"]
    temperature = config["model"].get("temperature", 0.2)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, temperature=temperature)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, temperature=temperature)

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)

    else:
        raise ValueError(
            f"Unsupported model provider: '{provider}'. "
            f"Supported providers: openai, anthropic, google. "
            f"Edit the 'model.provider' key in swarm_config.yml."
        )


def validate_env(config: dict) -> list[str]:
    """Validate that required environment variables are present.

    Returns a list of warning messages for missing optional keys.
    Does NOT raise for optional keys — only for the primary model key.
    """
    warnings = []

    # Check primary model key
    required_key = config["model"].get("env_key", "OPENAI_API_KEY")
    if not os.getenv(required_key):
        raise EnvironmentError(
            f"Required environment variable '{required_key}' is not set.\n"
            f"Copy .env.example to .env and add your API key."
        )

    # Check tool-specific optional keys
    tool_env_keys = {
        "search_you_engine": "YOU_API_KEY",
    }
    for tool_name, tool_spec in config["tools"].items():
        func_name = tool_spec.get("function", "")
        if func_name in tool_env_keys:
            env_key = tool_env_keys[func_name]
            if not os.getenv(env_key):
                warnings.append(
                    f"Tool '{tool_name}' requires '{env_key}' — "
                    f"it will fail at runtime if called."
                )

    return warnings
