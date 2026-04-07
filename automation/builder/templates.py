from __future__ import annotations

from automation.builder.models import PersonaSpec, SwarmSpec, ToolSpec, slugify_name

BUILTIN_TOOL_REGISTRY = {
    "search_literature": ToolSpec(
        module="automation.tools",
        function="search_pubmed",
        description="Search PubMed for peer-reviewed biomedical literature",
    ),
    "search_web": ToolSpec(
        module="automation.tools",
        function="search_you_engine",
        description="Search the live web via You.com API",
    ),
    "check_schema_org": ToolSpec(
        module="automation.tools",
        function="check_schema_org",
        description="Validate terms against the Schema.org vocabulary",
    ),
    "write_section": ToolSpec(
        module="automation.tools",
        function="write_manuscript_section",
        description="Write a drafted section to disk as Markdown",
    ),
    "append_traceability": ToolSpec(
        module="automation.tools",
        function="append_traceability_matrix",
        description="Log a fact and its source to the Knowledge Traceability Matrix",
    ),
    "search_kb": ToolSpec(
        module="automation.tools",
        function="search_knowledge_base",
        description="Search the local Knowledge Base documents",
    ),
    "scrape_page": ToolSpec(
        module="automation.tools",
        function="scrape_webpage",
        description="Fetch and extract full text content from a URL",
    ),
    "search_preprints": ToolSpec(
        module="automation.tools",
        function="search_semantic_scholar",
        description="Search Semantic Scholar for preprints and recent academic papers",
    ),
    "trace_literature_network": ToolSpec(
        module="automation.tools",
        function="trace_literature_network",
        description="Expand a major paper through its references and lead authors",
    ),
    "you_research": ToolSpec(
        module="automation.tools",
        function="you_research",
        description="Use You.com Research for synthesised multi-source web answers",
    ),
    "lookup_doi": ToolSpec(
        module="automation.tools",
        function="lookup_doi",
        description="Look up full citation metadata via Europe PMC and Crossref",
    ),
    "git_snapshot": ToolSpec(
        module="automation.tools",
        function="git_commit_snapshot",
        description="Commit swarm output files for version-controlled audit trail",
    ),
}

ARCHETYPE_SPECS = {
    "orchestrator": {
        "icon": "👑",
        "role": "Orchestrator and synthesizer",
        "tools": ["search_literature", "search_web", "search_kb", "append_traceability"],
        "core_mission": "Coordinate the swarm, route specialist work, and merge findings into a coherent plan.",
        "domain_focus": [
            "task framing and decomposition",
            "evidence synthesis across specialists",
            "conflict resolution between sources or methods",
        ],
        "kb_focus": [
            "project scope notes",
            "shared bibliographies",
            "high-level definitions and constraints",
        ],
        "behavior_rules": [
            "start by defining the user objective and target output",
            "route sub-questions to the most appropriate specialist rather than broadcasting everything",
            "maintain a clear synthesis path to the final writer",
        ],
    },
    "domain-specialist": {
        "icon": "🧠",
        "role": "Domain specialist",
        "tools": [
            "search_literature",
            "search_preprints",
            "search_web",
            "search_kb",
            "scrape_page",
            "lookup_doi",
            "append_traceability",
        ],
        "core_mission": "Investigate the core substantive questions in the target domain using primary and secondary sources.",
        "domain_focus": [
            "major constructs and definitions",
            "key empirical findings",
            "important limitations and disagreements",
        ],
        "kb_focus": [
            "domain-specific review papers",
            "reference documents and standards",
            "local notes or literature packets",
        ],
        "behavior_rules": [
            "separate strong evidence from weak or indirect claims",
            "look up citation metadata when a reference seems central",
            "log important findings to the traceability matrix",
        ],
    },
    "literature-scout": {
        "icon": "📚",
        "role": "Literature scout for citation chaining and author-trail expansion",
        "tools": [
            "search_literature",
            "search_preprints",
            "trace_literature_network",
            "lookup_doi",
            "scrape_page",
            "append_traceability",
        ],
        "core_mission": "Find the landmark papers in the field and expand from them through references, lead authors, and adjacent citation clusters.",
        "domain_focus": [
            "landmark reviews and meta-analyses",
            "citation clusters around foundational papers",
            "author networks and follow-on studies",
        ],
        "kb_focus": [
            "shared bibliographies",
            "reading lists and literature maps",
            "field overviews and consensus papers",
        ],
        "behavior_rules": [
            "start from a high-yield seed paper whenever possible",
            "use literature-network tracing before falling back to broad web search",
            "distinguish clearly between seed papers, references, and author-derived follow-ons",
        ],
    },
    "methods-reviewer": {
        "icon": "📊",
        "role": "Methods and evidence-quality reviewer",
        "tools": [
            "search_literature",
            "search_preprints",
            "search_web",
            "search_kb",
            "scrape_page",
            "lookup_doi",
            "append_traceability",
        ],
        "core_mission": "Check whether study design, measurement quality, and evidence synthesis justify the claims being made.",
        "domain_focus": [
            "study design and bias",
            "measurement quality and instrumentation",
            "uncertainty, limitations, and comparability across studies",
        ],
        "kb_focus": [
            "methods papers",
            "quality appraisal guides",
            "measurement notes and codebooks",
        ],
        "behavior_rules": [
            "challenge overconfident claims that exceed the underlying evidence",
            "look for design flaws before accepting strong conclusions",
            "surface what remains uncertain, not just what appears supported",
        ],
    },
    "intervention-specialist": {
        "icon": "🛟",
        "role": "Intervention and applied-practice specialist",
        "tools": [
            "search_literature",
            "search_preprints",
            "search_web",
            "search_kb",
            "scrape_page",
            "lookup_doi",
            "append_traceability",
        ],
        "core_mission": "Evaluate intervention options, implementation constraints, and applied implications for the target domain.",
        "domain_focus": [
            "interventions and programs",
            "practical implementation pathways",
            "evidence for applied recommendations",
        ],
        "kb_focus": [
            "intervention summaries",
            "practice guidelines",
            "implementation notes and workflows",
        ],
        "behavior_rules": [
            "prefer systematic reviews and high-quality comparative evidence when available",
            "separate practical implications from stronger causal conclusions",
            "note where intervention evidence is thin or non-transferable",
        ],
    },
    "journalist": {
        "icon": "✍️",
        "role": "Final writer and documentarian",
        "tools": ["write_section", "append_traceability", "git_snapshot"],
        "core_mission": "Write the final output clearly, neutrally, and in a form the user can reuse.",
        "domain_focus": [
            "clear structure and readable synthesis",
            "source-aware writing with references",
            "faithful representation of specialist findings",
        ],
        "kb_focus": [
            "style guides",
            "report templates",
            "reference formatting notes",
        ],
        "behavior_rules": [
            "do not invent claims that specialists did not support",
            "preserve caveats and uncertainty in the final draft",
            "produce structured outputs with references and limitations",
        ],
    },
}

AVAILABLE_ARCHETYPES = sorted(ARCHETYPE_SPECS.keys())


def build_persona_from_archetype(
    archetype: str,
    domain: str,
    name: str | None = None,
    role: str | None = None,
) -> PersonaSpec:
    if archetype not in ARCHETYPE_SPECS:
        raise ValueError(f"unknown archetype '{archetype}'")

    spec = ARCHETYPE_SPECS[archetype]
    persona_name = name or archetype.replace("-", " ").title()
    persona_role = role or spec["role"]

    return PersonaSpec(
        name=persona_name,
        folder_name=slugify_name(persona_name),
        icon=spec["icon"],
        role=persona_role,
        tools=list(spec["tools"]),
        core_mission=spec["core_mission"],
        domain_focus=[f"{domain}: {item}" for item in spec["domain_focus"]],
        kb_focus=[f"{domain}: {item}" for item in spec["kb_focus"]],
        behavior_rules=list(spec["behavior_rules"]),
    )


def build_starter_swarm_spec(
    domain: str,
    swarm_name: str,
    swarm_description: str,
    model_provider: str = "openai",
    model_name: str = "gpt-4o",
    model_env_key: str = "OPENAI_API_KEY",
) -> SwarmSpec:
    personas = [
        build_persona_from_archetype("orchestrator", domain, name="Coordinator"),
        build_persona_from_archetype("literature-scout", domain, name="LiteratureScout"),
        build_persona_from_archetype("domain-specialist", domain, name="DomainSpecialist"),
        build_persona_from_archetype("methods-reviewer", domain, name="MethodsReviewer"),
        build_persona_from_archetype("journalist", domain, name="Journalist"),
    ]
    return SwarmSpec(
        swarm_name=swarm_name,
        swarm_description=swarm_description,
        domain=domain,
        model_provider=model_provider,
        model_name=model_name,
        model_env_key=model_env_key,
        personas=personas,
        orchestrator_agent="Coordinator",
        journalist_agent="Journalist",
        reviewer_banned_words=[
            "groundbreaking",
            "revolutionary",
            "game-changing",
            "paradigm-shifting",
            "unprecedented",
        ],
        reviewer_required_elements=[
            "clear task framing",
            "a short limitations or uncertainty section",
            "source-aware in-text citations when claims rely on external evidence",
            "a final References or Sources section",
        ],
        reviewer_rejection_patterns=[
            "any unsupported factual claim presented with certainty",
        ],
        tool_registry=BUILTIN_TOOL_REGISTRY,
    )