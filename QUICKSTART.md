# 🚀 Quickstart: Build Your Own Research Swarm in 5 Minutes

This guide takes you from `git clone` to running your first autonomous multi-agent research task, whether you're working in **Regulatory Toxicology**, **Climate Science**, **Legal Tech**, or any other domain.

---

## Prerequisites

- **Python 3.10+** installed
- An **OpenAI API key** (or Anthropic/Google — see [Model Configuration](#configure-your-llm))
- *(Optional)* A **You.com API key** for live web search

---

## Step 1: Clone & Setup

```bash
git clone https://github.com/dhuzard/FAIR-NAMs-Squad.git
cd FAIR-NAMs-Squad
```

### Option A: Makefile (Recommended on Windows)
```bash
make setup
```
This creates a virtual environment, installs all dependencies, and copies `.env.example` to `.env`.

### Option B: Manual Setup
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e .
copy .env.example .env
```

### Option C: Docker
```bash
docker compose build
```

---

## Step 2: Add Your API Keys

Edit the `.env` file and paste your keys:

```env
OPENAI_API_KEY=sk-your-actual-key-here
YOU_API_KEY=your-you-dot-com-key-here   # optional
```

---

## Step 3: Verify Your Configuration

```bash
make info
# or: python -m automation.main info
```

This prints your swarm's current configuration: personas, tools, model, and reviewer settings.

---

## Step 4: Run Your First Task

```bash
make run PROMPT="Search for the latest developments in your field and write a summary to disk."
# or: python -m automation.main execute "Your prompt here"
```

Once the terminal finishes, open the `./Drafts/` folder — your agents wrote their outputs directly to disk as Markdown files.

---

## Step 5: Customize for Your Domain

This is where the framework becomes **yours**. You have two options:

### Option A: Edit the Existing Configuration

Open `swarm_config.yml` and modify:

1. **Personas** — Change names, roles, and persona files
2. **Tools** — Swap `search_pubmed` for your domain's literature API
3. **Reviewer-2** — Update banned words, required elements, and tone
4. **Model** — Switch from OpenAI to Anthropic or Google

### Option B: Scaffold a Fresh Domain

```bash
make scaffold DOMAIN="Climate Science"
# or: python -m automation.main scaffold "Climate Science"
```

This creates default persona directories with template `persona.md` files you can fill in.

---

## Configuration Deep Dive

### Configure Your LLM

Edit the `model:` block in `swarm_config.yml`:

```yaml
# OpenAI (default)
model:
  provider: "openai"
  name: "gpt-4o"
  env_key: "OPENAI_API_KEY"

# Anthropic Claude
model:
  provider: "anthropic"
  name: "claude-sonnet-4-20250514"
  env_key: "ANTHROPIC_API_KEY"

# Google Gemini
model:
  provider: "google"
  name: "gemini-2.0-flash"
  env_key: "GOOGLE_API_KEY"
```

Install the provider's optional dependencies if needed:
```bash
pip install -e ".[anthropic]"   # for Claude
pip install -e ".[google]"      # for Gemini
```

### Add Custom Tools

1. Create a Python function decorated with `@tool` (in `automation/tools.py` or a new module)
2. Register it in `swarm_config.yml`:

```yaml
tools:
  my_custom_search:
    module: "automation.tools"      # or "my_module.my_file"
    function: "my_search_function"
    description: "Searches my custom database"
```

3. Assign it to personas that should use it:

```yaml
personas:
  - name: "Researcher"
    tools: ["my_custom_search", "search_web"]
```

### Customize Reviewer-2

The adversarial reviewer's constraints are fully configurable:

```yaml
reviewer:
  enabled: true
  max_revision_loops: 3
  banned_words: ["guaranteed", "risk-free", "slam dunk"]
  required_elements: ["Bluebook citations", "Case number references"]
  tone: "formal legal analysis"
```

Or disable it entirely:
```yaml
reviewer:
  enabled: false
```

### Add Knowledge Base Documents

1. Drop PDFs, Markdown, or text files into `agents/<PersonaName>/KB/`
2. Vectorize them: `make ingest`
3. The `search_knowledge_base` tool will now retrieve from those documents

---

## Architecture Overview

```
swarm_config.yml          ← YOU EDIT THIS (personas, tools, reviewer, model)
agents/*/persona.md       ← YOU EDIT THESE (agent expertise & behavior)
agents/*/KB/              ← YOU DROP DOCUMENTS HERE

automation/config.py      ← Loads config, builds prompts (don't edit)
automation/graph.py       ← LangGraph state machine (don't edit)
automation/main.py        ← CLI entry point (don't edit)
automation/tools.py       ← Tool functions (extend, don't modify existing)

Drafts/                   ← Agent outputs land here
Knowledge_Traceability_Matrix.md  ← Epistemic audit trail
```

**The design principle:** customize your swarm by editing YAML and Markdown — never Python code.

---

## Troubleshooting

| Problem | Solution |
|:---|:---|
| `CONFIG ERROR: Configuration file not found` | Ensure `swarm_config.yml` exists in the project root |
| `ENV ERROR: Required environment variable...` | Edit `.env` with your API key |
| `Error loading tool...` | Check `module` and `function` paths in `swarm_config.yml` |
| `No Knowledge Base found` | Run `make ingest` or `python -m automation.ingest` |
| Reviewer-2 loops forever | Increase `max_revision_loops` or check `banned_words` aren't too aggressive |
