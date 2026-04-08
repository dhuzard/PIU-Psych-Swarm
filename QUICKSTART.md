# Quickstart: Run Research Swarm

This guide takes you from clone to first run in five steps.

## Prerequisites

- Python 3.10+
- An OpenAI API key (or another supported provider key — see `swarm_config.yml`)
- Optional: a You.com API key for live web search

Platform notes:
- Linux or Windows WSL: install `python3`, `python3-venv`, and `make`
- Native Windows: use PowerShell with the `py` launcher; `make` is not required

---

## Step 1: Clone and Setup

### Linux or Windows WSL

```bash
git clone https://github.com/dhuzard/piu-psych-swarm.git
cd piu-psych-swarm
make setup
```

If your system does not provide `python3` yet:

```bash
sudo apt update && sudo apt install -y python3 python3-venv make
```

### Native Windows (PowerShell)

```powershell
git clone https://github.com/dhuzard/piu-psych-swarm.git
cd piu-psych-swarm
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

---

## Step 2: Add API Keys

Edit `.env` with the required keys:

```env
OPENAI_API_KEY=sk-your-key
YOU_API_KEY=your-you-key    # optional — enables live web search
```

---

## Step 3: Configure Your Team

The default template contains five generic personas. Before running, either:

**Option A — Use the interactive builder** to define your domain and team:

```bash
python -m automation.main init
```

**Option B — Edit the template directly:**

1. Open `swarm_config.yml` and set `swarm.name` and `swarm.description`.
2. Rename `Specialist1` and `Specialist2` to match your domain roles.
3. Rename the corresponding folders in `agents/` to match.
4. Edit each `agents/*/persona.md` to define the agent's focus and behavior.

**Option C — Deploy a ready-made example** (e.g., the PIU psychiatry team):

```bash
cp examples/piu_psychiatry/swarm_config.yml .
cp -r examples/piu_psychiatry/agents .
```

---

## Step 4: Build the Knowledge Base

Vectorize any documents you placed in `agents/*/KB/`:

### Linux or Windows WSL

```bash
make ingest
```

### Native Windows (PowerShell)

```powershell
.\.venv\Scripts\python -m automation.ingest
```

This creates a local ChromaDB vector store from the KB files so agents can search them. If your KB folders are empty, the swarm will still run — it will rely on live search tools instead.

---

## Step 5: Verify the Team and Run

### Linux or Windows WSL

```bash
make info    # inspect the active team, tools, and reviewer config
make run PROMPT="Your research question here"
```

### Native Windows (PowerShell)

```powershell
.\.venv\Scripts\python -m automation.main info
.\.venv\Scripts\python -m automation.main execute "Your research question here"
```

---

## Structured Report Modes

Use `report` instead of `execute` to request a specific output format:

```bash
python -m automation.main report "Your question" --mode scoping-review
python -m automation.main report "Your question" --mode evidence-brief
python -m automation.main report "Your question" --mode grant-support
python -m automation.main report "Your question" --mode manuscript-draft
```

Available modes: `scoping-review`, `narrative-review`, `evidence-brief`, `manuscript-draft`, `grant-support`, `journalistic-brief`, `pediatric-screen`, `young-adult-screen`, `general-adult-screen`

---

## Key Working Files

After a run, check these locations for outputs:

- `Drafts/` — all generated documents and section drafts
- `Knowledge_Traceability_Matrix.md` — evidence audit trail with epistemic tags
- `Drafts/run_metrics.json` — token usage and estimated cost per run

---

## Troubleshooting

| Problem | Solution |
| :--- | :--- |
| `CONFIG ERROR` | Ensure `swarm_config.yml` exists and is valid YAML. Run `make doctor`. |
| `ENV ERROR` | Add required API keys to `.env` |
| No Knowledge Base found | Run `make ingest` |
| Tool import failures | Run `make setup` again or install missing dependencies into `.venv` |
| Persona not found | Ensure persona names in `swarm_config.yml` match folder names in `agents/` |
| Empty outputs | Check `Drafts/` folder; run `make info` to verify tool wiring |

Run `python -m automation.main doctor` at any time to validate your configuration.
