# PIU Psych Swarm

A configurable multi-agent framework for psychiatric research on problematic internet use.

> The repository is preconfigured for psychiatric and behavioral-science work on problematic internet use, while remaining configurable for other research domains.

## Focus

PIU Psych Swarm is a LangGraph-based multi-agent system that researches, debates, and documents psychiatric questions about problematic internet use, including internet gaming disorder where relevant.

The repository is currently optimized for:

- clinically cautious synthesis that separates high engagement from impairment
- literature-backed summaries with in-text citations and references
- reusable local knowledge bases for subagent-specific expertise
- structured drafting workflows for reviews, evidence briefs, and study notes

## Quickstart

### Linux or Windows WSL

Requirements:

- Python 3.10+
- `python3-venv`
- `make`

```bash
git clone https://github.com/dhuzard/piu-psych-swarm.git
cd piu-psych-swarm
make setup
make ingest
make run PROMPT="Review the psychiatric literature on problematic internet use in adolescents, including prevalence, comorbidity, mechanisms, and interventions."
```

If `make setup` fails because `python3` is missing, install it first. On Ubuntu or WSL:

```bash
sudo apt update
sudo apt install -y python3 python3-venv make
```

### Native Windows (PowerShell)

Use PowerShell for native Windows setup. This avoids requiring GNU Make.

```powershell
git clone https://github.com/dhuzard/piu-psych-swarm.git
cd piu-psych-swarm
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python -m automation.ingest
.\.venv\Scripts\python -m automation.main execute "Review the psychiatric literature on problematic internet use in adolescents, including prevalence, comorbidity, mechanisms, and interventions."
```

## Create Your Own Swarm

The repository now includes the first six phases of an interactive swarm builder.

Use the builder-backed command:

```bash
python -m automation.main init
```

Current capabilities:

- create a valid `swarm_config.yml` from a typed builder spec
- generate persona markdown files and `agents/*/KB/` folders
- start from a recommended starter team or define specialist personas interactively with richer prompts
- preview file-level diffs before writes occur
- inspect the active swarm with `python -m automation.main preview`
- validate the active swarm with `python -m automation.main doctor`
- add a persona with `python -m automation.main persona add`
- edit a persona with `python -m automation.main persona edit`
- configure orchestration and HITL with `python -m automation.main team configure`
- configure reviewer policy with `python -m automation.main review configure`
- configure the primary model with `python -m automation.main model configure`
- configure swarm metadata with `python -m automation.main metadata configure`
- curate the active tool registry with `python -m automation.main tools configure`
- add a tool with `python -m automation.main tools add`
- edit a tool with `python -m automation.main tools edit`
- remove a tool with `python -m automation.main tools remove`
- auto-repair safe filesystem issues with `python -m automation.main doctor --fix`

For a non-interactive starter swarm:

```bash
python -m automation.main init --no-interactive --domain "Climate Science" --name "Climate Science Swarm"
```

## Persona Squad

| Agent | Icon | Role | Technical Focus |
| :--- | :--- | :--- | :--- |
| Dr. Nexus | 👑 | Orchestrator | Coordination, synthesis, and reference management |
| ClinicalPsych | 🧠 | Clinical specialist | Diagnosis, impairment, and comorbidity |
| EpiScope | 📊 | Epidemiology specialist | Prevalence, psychometrics, risk and protective factors |
| LitScout | 📚 | Literature specialist | Citation chaining, reference mining, and author-trail expansion |
| NeuroCogs | 🧪 | Mechanisms specialist | Reward, executive control, neurocognition, imaging |
| CarePath | 🛟 | Intervention specialist | Prevention, treatment, and care pathways |
| Journalist | ✍️ | Scribe | Neutral, professional documentation and reporting |

## Typical Workflow

```bash
make ingest
make info
make run PROMPT="Create a scoping review outline for problematic internet use in university students."
```

Useful working files:

- Drafts/piu_prompt_set.md
- Drafts/piu_study_workflow_template.md
- Article_Draft.md
- Knowledge_Traceability_Matrix.md

## Core Tooling

| Tool | Purpose |
| :--- | :--- |
| search_pubmed | Search peer-reviewed biomedical and psychiatric literature |
| trace_literature_network | Expand a major paper via its references and lead authors |
| search_you_engine | Search the live web |
| search_knowledge_base | Search local PIU literature packets in agents/*/KB/ |
| scrape_webpage | Pull full-text content from URLs |
| append_traceability_matrix | Log evidence and epistemic status |
| write_manuscript_section | Write markdown outputs into Drafts/ |

## Repository Layout

- swarm_config.yml: Active swarm definition
- agents/: Personas and local knowledge bases
- automation/: Runtime, tools, ingestion, and graph logic
- Drafts/: Prompt packs, workflow templates, and generated outputs
- Knowledge_Traceability_Matrix.md: Running audit trail for evidence use

## Next Step

The next major module should be an interactive swarm builder so users can create their own personas, choose tools, set reviewer rules, and define orchestration behavior without hand-editing YAML.

Implemented in Phase 1:

- a typed `SwarmSpec` builder core
- file generation for config, personas, and KB folders
- a first `swarm init` command backed by that builder

Implemented in Phase 2:

- richer interactive prompts with `Questionary` fallback to plain prompts when needed
- `swarm preview` for readable inspection of the current team and tool registry
- `swarm doctor` for config, file, KB, tool-import, and environment checks

Implemented in Phase 3:

- file-level diff previews before builder writes
- `swarm persona add` for adding a persona into an existing swarm
- `swarm persona edit` for editing an existing persona safely
- `swarm doctor --fix` for safe repairs of missing KB directories and `.gitkeep` files

Implemented in Phase 4:

- `swarm team configure` for orchestrator, routing, and HITL configuration
- `swarm review configure` for reviewer tone, bans, required elements, and model overrides
- non-interactive option-driven config updates backed by the same builder core used by the interactive flow

Implemented in Phase 5:

- `swarm model configure` for provider, model name, temperature, and env-key changes
- `swarm metadata configure` for name, description, output paths, and epistemic tags
- `swarm tools configure` for active tool-registry curation with persona-tool synchronization

Implemented in Phase 6:

- `swarm tools add` for adding built-in or custom tool registry entries
- `swarm tools edit` for updating existing tool registry entries
- `swarm tools remove` for removing tool registry entries while protecting personas from ending up tool-less

Recommended next implementation direction:

- Keep `Typer` as the command surface because the repo already uses it successfully.
- Add `Rich` for previews, validation panels, and diff-style summaries.
- Keep `Questionary` and extend the wizard into persona editing flows.
- Keep the builder engine separate from the CLI so the same core can later power a richer TUI or web UI.
- Add template management, richer policy presets, and optional higher-level swarm blueprints on top of the existing targeted edit commands.

Planned command family:

- `swarm init`: create a new swarm from an interactive wizard
- `swarm persona add`: create a persona with role, tools, KB folder, and behavior template
- `swarm persona edit`: update an existing persona interactively
- `swarm team configure`: choose orchestrator, journalist, routing limits, and HITL settings
- `swarm review configure`: set reviewer rules, banned words, and required elements
- `swarm model configure`: change provider, model name, temperature, and env key
- `swarm metadata configure`: change swarm name, description, domain label, output paths, and epistemic tags
- `swarm tools configure`: curate the active tool registry used by the current swarm
- `swarm tools add`: add a built-in or custom tool registry entry
- `swarm tools edit`: update a tool registry entry
- `swarm tools remove`: remove a tool registry entry safely
- `swarm preview`: render the current team, tool map, and config summary
- `swarm doctor`: validate the generated config, persona files, KB layout, and tool wiring
- `swarm doctor --fix`: repair the safe filesystem issues automatically

Design principle:

Build a schema-driven team-creation module first, then place an interactive CLI on top of it. The solid foundation is the model and validator layer, not the prompt loop.

See [INTERACTIVE_SWARM_BUILDER_PLAN.md](INTERACTIVE_SWARM_BUILDER_PLAN.md) for the detailed architecture and implementation plan.

## Notes

- The active team is controlled by swarm_config.yml.
- KB ingestion and KB search now follow the configured personas rather than every folder under agents/.
- The repository is currently curated for PIU-focused psychiatric research workflows.
