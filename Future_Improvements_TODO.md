# PIU Psych Swarm — Improvements & Fix Tracker

Items are grouped by theme. `[x]` = implemented and pushed. `[ ]` = pending.

---

## Architecture: Multi-Agent Refactor

- [x] Rewrite `graph.py` as a true supervisor multi-agent pattern — each persona is a
      separate LangGraph node with its own system prompt and scoped tool set
- [x] Add per-persona helper functions to `config.py`:
      `get_persona_config`, `load_tools_for_persona`, `build_agent_system_prompt`
- [x] Update `main.py` `execute()` to pass task string as initial state
      (no swarm-level system prompt injected from CLI)
- [x] Add `orchestrator:` section to `swarm_config.yml`
      (`agent`, `journalist`, `max_agent_calls`, `max_tool_rounds_per_agent`)
- [x] Remove `truncate(300)` from `system_prompt_template` persona injection —
      full persona.md content now reaches the model
- [x] Mark `system_prompt_template` as `LEGACY — NOT USED` in `swarm_config.yml`
- [x] Mark `build_system_prompt()` as legacy in `config.py` docstring
- [ ] Remove `load_tools()` from `config.py` — dead code, no longer called at runtime
      (kept for backward compat with custom scripts; remove in a breaking release)

---

## Orchestrator (Dr. Nexus)

- [x] Structured output routing via `OrchestratorDecision` Pydantic model
      (`reasoning`, `next_agents: list[str]`, `instructions`)
- [x] Parallel specialist fan-out via LangGraph `Send` — orchestrator can dispatch
      multiple specialists simultaneously when sub-questions are independent
- [x] Add `SPECIALISTS ALREADY CONSULTED` list to orchestrator routing prompt
      (derived from `agent_outputs.keys()`) to prevent redundant re-routing
- [x] Fix `agent_call_count` to increment only for specialist dispatches
      (not for Journalist or END routing); gives full `max_agent_calls` budget
      for actual research calls
- [ ] Allow per-agent instructions in parallel dispatch — currently all parallel
      specialists receive the same `instructions` string; a `list[AgentAssignment]`
      schema would allow differentiated guidance per parallel target
- [ ] `create_model(config)` is instantiated fresh on every orchestrator and
      specialist node call; cache or pre-bind at graph-build time to reduce overhead

---

## Tool Bugs & Safety

- [x] Fix `_run_tool_loop` bug — `messages = tool_result["messages"]` replaced with
      `messages = messages + tool_result["messages"]`; prior context was being
      discarded after the first tool call in every agent node
- [x] Fix `git_commit_snapshot` — replace `git add -A` with explicit safe paths
      (`Drafts/` + traceability matrix read from config); eliminates risk of
      staging `.env`, credentials, notebooks, or binaries
- [ ] `write_manuscript_section` silently overwrites on repeated calls with the same
      section name — add a timestamp suffix or version counter to the filename
- [ ] `append_traceability_matrix` appends raw markdown table rows with no structure
      validation — add a check that the target file exists and its table header
      is intact before writing, to prevent corruption on repeated runs

---

## Tool Capability

- [x] `search_pubmed`: switch from `esummary` (title + PMID only) to `efetch` with
      `rettype=abstract&retmode=xml`; parses full abstract including labelled sections
- [x] Add `search_semantic_scholar` tool (Semantic Scholar Graph API, no key needed);
      indexes preprints, arXiv, CHI, and 2024–2026 papers absent from PubMed;
      registered as `search_preprints` and assigned to all four research specialists
- [x] Add `Search Fallback` rule to all specialist `persona.md` files:
      if `search_literature` returns empty → try `search_preprints` → then `search_web`
- [x] Fix `search_you_engine` base URL (legacy `ydc-index.io` endpoint → `api.ydc-index.io`)
      and update response parsing for current API response structure
- [x] Add `you_research` tool (You.com Research / RAG API) — synthesised answer with citations;
      assigned to ClinicalPsych, EpiScope, NeuroCogs, CarePath
- [x] Replace `scrape_webpage` BeautifulSoup implementation with You.com Contents API
      (`/news?url=...`); BeautifulSoup kept as fallback for API unavailability
- [x] Assign `scrape_page` to all four research specialists in `swarm_config.yml`
      (was registered but unassigned)
- [ ] Add Europe PMC or Crossref lookup for DOI resolution and richer citation metadata
      (DOI, publication date, open-access PDF link)
- [ ] Replace deprecated `langchain_community` embedding/vectorstore imports in
      `ingest.py` with current `langchain-huggingface` / `langchain-chroma` paths
- [ ] Add async tool execution within specialists — currently all tool calls are
      synchronous and sequential; `asyncio` + `ToolNode` async variants would allow
      parallel `search_pubmed` + `search_semantic_scholar` within one specialist call
- [ ] Add token/cost tracking per agent per run — log input/output tokens and
      estimated cost to a `run_metrics.json` alongside each Drafts/ output

---

## Reviewer-2 (Adversarial Checkpoint)

- [x] Reviewer model diversity — `create_reviewer_model()` in `config.py` merges
      `reviewer.model` overrides onto the base config; active config sets
      `temperature: 0.8` for genuinely adversarial critique vs `0.2` for agents
- [x] Add AI-chatbot construct instability check to `reviewer.required_elements` —
      reviewer rejects any output on AI/LLM use that lacks a note on whether
      evidence meets clinical-level impairment criteria
- [ ] Reviewer uses the same model name as research agents (only temperature differs);
      for maximum adversarial diversity, configure a different model family
      (e.g., Anthropic claude-opus when agents run on gpt-4o, or vice versa)
- [ ] Add reviewer check: prevent prevalence claims without instrument and cut-off
      caveats (already in Phase 3 below — consolidate)

---

## Knowledge Base & Literature

- [x] Add 2025–2026 AI-dependence literature to all five agent KBs:
      `ClinicalPsych`, `EpiScope`, `NeuroCogs`, `CarePath`, `DrNexus`
      (15 peer-reviewed and preprint references across construct debate,
      scales, reward mechanisms, mental health correlates, and care implications)
- [ ] Add separate KB packets for social media disorder, gaming disorder (IGD),
      and smartphone overuse (currently all live in the same general PIU KB)
- [ ] Add intervention summaries for family-based, school-based, and telehealth
      pathways to `CarePath/KB/`
- [ ] Add a traceability-matrix auto-header that inserts task date, target population,
      and construct when a new run begins

---

## Clinical Workflow & Output Templates

- [ ] Add explicit output templates for scoping review, narrative review, and
      evidence brief modes (selectable via CLI flag or prompt prefix)
- [ ] Add optional screening prompts for adolescent, university, and general-adult
      populations (different PIU base-rates, instruments, and clinical thresholds apply)
- [ ] Add a `report-mode` command that writes directly into a dated draft template
      (`Drafts/YYYY-MM-DD_<task>.md`) and increments on re-runs
- [ ] Add prompt packs for grant support, manuscript drafting, and journalistic briefings

---

## Methodological Guardrails (Reviewer Rules)

- [ ] Add reviewer check: reject outputs that imply all high-frequency internet use
      is pathological (overpathologizing guard)
- [ ] Add reviewer check: reject prevalence claims that do not name the screening
      instrument and cut-off used
- [ ] Add reviewer check: require explicit disorder-status clarification whenever
      IGD or internet gaming disorder is mentioned (ICD-11 vs DSM-5 Section III)
