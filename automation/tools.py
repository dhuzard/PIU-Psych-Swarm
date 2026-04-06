"""
tools.py — Tool Functions for the Research Swarm

Each function decorated with @tool becomes available to the LangGraph agents.
Tools are registered in swarm_config.yml and dynamically loaded by config.py.

To add a custom tool:
  1. Create a function decorated with @tool in this file (or a new module)
  2. Register it in swarm_config.yml under the 'tools:' section
  3. Assign it to one or more persona's tool lists

Built-in Tools:
  - search_pubmed              : Search PubMed and return full title + abstract
  - search_semantic_scholar    : Search Semantic Scholar (indexes preprints + journals)
  - check_schema_org           : Validate terms against Schema.org vocabulary
  - write_manuscript_section   : Write a Markdown section to the Drafts/ directory
  - search_you_engine          : Search the live web via You.com API
  - append_traceability_matrix : Log a fact to the Knowledge Traceability Matrix
  - search_knowledge_base      : Search local vectorized KB documents
  - scrape_webpage             : Fetch full text content from a URL
  - git_commit_snapshot        : Auto-commit output files for version-controlled audit trail
"""

import os
import subprocess
from pathlib import Path
import requests
from langchain_core.tools import tool


# ═══════════════════════════════════════════════════════
# RESEARCH TOOLS (Domain-Specific — swap these per domain)
# ═══════════════════════════════════════════════════════


@tool
def search_pubmed(query: str, max_results: int = 3) -> str:
    """Searches PubMed for a given query and returns title, journal, PMID,
    and full abstract for each result. Use this for peer-reviewed biomedical
    literature. If results are empty or abstracts are missing, follow up with
    search_semantic_scholar or search_web for preprints and recent papers."""
    import xml.etree.ElementTree as ET

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    try:
        search_resp = requests.get(
            base_url,
            params={
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": max_results,
            },
        )
        search_resp.raise_for_status()
        id_list = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return (
                "No results found on PubMed for this query. "
                "Try search_semantic_scholar or search_web for preprints and 2024–2026 papers."
            )

        # Fetch full records including abstracts via efetch
        fetch_resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(id_list),
                "rettype": "abstract",
                "retmode": "xml",
            },
        )
        fetch_resp.raise_for_status()

        root = ET.fromstring(fetch_resp.text)
        output = []

        for article in root.findall(".//PubmedArticle"):
            citation = article.find("MedlineCitation")
            if citation is None:
                continue

            pmid_el = citation.find("PMID")
            pmid = pmid_el.text if pmid_el is not None else "Unknown"

            art = citation.find("Article")
            if art is None:
                continue

            title_el = art.find("ArticleTitle")
            title = "".join(title_el.itertext()) if title_el is not None else "No title"

            journal_el = art.find("Journal/Title")
            journal = journal_el.text if journal_el is not None else "Unknown journal"

            year_el = art.find(".//PubDate/Year")
            year = year_el.text if year_el is not None else ""

            # AbstractText may be a single element or multiple labelled sections
            abstract_parts = []
            for ab in art.findall(".//AbstractText"):
                label = ab.get("Label")
                text = "".join(ab.itertext()).strip()
                if label:
                    abstract_parts.append(f"{label}: {text}")
                elif text:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available."

            output.append(
                f"Title: {title}\n"
                f"Journal: {journal} ({year})\n"
                f"PMID: {pmid}\n"
                f"Abstract: {abstract}"
            )

        if not output:
            return (
                "PubMed returned records but abstracts could not be parsed. "
                "Try search_semantic_scholar for this query."
            )

        return "\n\n---\n\n".join(output)

    except Exception as e:
        return f"Error querying PubMed: {e}"


@tool
def search_semantic_scholar(query: str, max_results: int = 5) -> str:
    """Searches Semantic Scholar for academic papers including preprints, conference
    papers, and journal articles. Unlike PubMed, Semantic Scholar indexes arXiv,
    bioRxiv, CHI, and recent 2024–2026 papers that may not yet appear on PubMed.

    Use this when search_pubmed returns no results, or when you need preprints,
    AI/HCI conference papers, or very recent publications.

    Args:
        query: Search terms (e.g., 'AI chatbot dependence problematic use 2025').
        max_results: Number of results to return (default 5, max 10).
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(max_results, 10),
        "fields": "title,abstract,year,authors,externalIds,venue,url",
    }
    headers = {"User-Agent": "PIU-Psych-Swarm/1.0 (Academic Research)"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        papers = data.get("data", [])
        if not papers:
            return (
                f"No results found on Semantic Scholar for: '{query}'. "
                "Try search_web or a shorter query."
            )

        output = []
        for paper in papers:
            title = paper.get("title", "No title")
            year = paper.get("year", "n.d.")
            venue = paper.get("venue", "")
            authors = ", ".join(
                a.get("name", "") for a in paper.get("authors", [])[:3]
            )
            if len(paper.get("authors", [])) > 3:
                authors += " et al."

            ext_ids = paper.get("externalIds", {})
            doi = ext_ids.get("DOI", "")
            arxiv = ext_ids.get("ArXiv", "")
            s2_url = paper.get("url", "")

            abstract = paper.get("abstract") or "No abstract available."
            # Cap abstract at 600 chars to keep output manageable
            if len(abstract) > 600:
                abstract = abstract[:600] + "…"

            id_line = " | ".join(filter(None, [
                f"DOI: {doi}" if doi else "",
                f"arXiv: {arxiv}" if arxiv else "",
                s2_url,
            ]))

            output.append(
                f"Title: {title}\n"
                f"Authors: {authors}\n"
                f"Year: {year} | Venue: {venue}\n"
                f"IDs: {id_line}\n"
                f"Abstract: {abstract}"
            )

        return "\n\n---\n\n".join(output)

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            return (
                "Semantic Scholar rate limit hit. Wait a moment and retry, "
                "or use search_web as an alternative."
            )
        return f"Semantic Scholar HTTP error: {e}"
    except Exception as e:
        return f"Error querying Semantic Scholar: {e}"


@tool
def check_schema_org(entity: str) -> str:
    """Checks if a given term exists natively in the Schema.org vocabulary.
    Pass abstract nouns like 'Dataset' or 'manufacturer'."""
    try:
        resp = requests.get(f"https://schema.org/{entity}")
        if resp.status_code == 200:
            return f"Entity '{entity}' exists in schema.org. It is structurally valid."
        else:
            return f"Entity '{entity}' NOT found natively in schema.org. Custom mapping required."
    except Exception as e:
        return f"Error contacting schema.org: {e}"


# ═══════════════════════════════════════════════════════
# I/O TOOLS (Domain-Agnostic)
# ═══════════════════════════════════════════════════════


@tool
def write_manuscript_section(section_name: str, content: str) -> str:
    """Writes a drafted section to the disk in the configured output directory.
    The file will be saved as a Markdown (.md) file."""
    # Use the config's output_dir if available, fallback to Drafts/
    drafts_dir = os.path.join(os.path.dirname(__file__), "..", "Drafts")
    os.makedirs(drafts_dir, exist_ok=True)
    filename = f"{section_name.lower().replace(' ', '_')}.md"
    filepath = os.path.join(drafts_dir, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"SUCCESS: Wrote '{section_name}' to {filepath}"
    except Exception as e:
        return f"FAILED to write file: {e}"


@tool
def append_traceability_matrix(fact: str, source: str, epistemic_tag: str) -> str:
    """Logs a documented fact and its source into the Knowledge Traceability Matrix.
    Use this IMMEDIATELY after using search tools to secure the epistemic integrity trail.

    Args:
        fact: The specific finding or claim to record.
        source: The URL, PMID, or document reference where this was found.
        epistemic_tag: One of [FACT], [INFERENCE], or [SPECULATION].
    """
    filepath = os.path.join(
        os.path.dirname(__file__), "..", "Knowledge_Traceability_Matrix.md"
    )
    try:
        new_row = (
            f"| *Live Search:* {source} | **Auto-Agent** | "
            f"{fact} | Automatically sourced and summarized via Tool API. | "
            f"**{epistemic_tag}** |\n"
        )
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(new_row)
        return f"SUCCESS: Logged '{epistemic_tag}' finding to Traceability Matrix."
    except Exception as e:
        return f"FAILED to append to Traceability Matrix: {e}"


# ═══════════════════════════════════════════════════════
# WEB SEARCH TOOLS (Domain-Agnostic)
# ═══════════════════════════════════════════════════════


@tool
def search_you_engine(query: str) -> str:
    """Searches the live web using the You.com API.
    Use this to find current news, web pages, or broad research that
    requires live web context outside of specialized literature databases."""
    api_key = os.getenv("YOU_API_KEY")
    if not api_key:
        return "ERROR: 'YOU_API_KEY' is not set in the environment variables."

    url = "https://ydc-index.io/v1/search"
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    params = {"query": query}

    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        snippets = []
        web_results = data.get("results", {}).get("web", [])
        if not web_results:
            return f"No web results found on You.com. Raw response structure: {list(data.keys())}"

        for count, hit in enumerate(web_results[:5]):
            title = hit.get("title", "No Title")
            link = hit.get("url", "No URL")
            description = "\n".join(hit.get("snippets", []))
            if not description:
                description = hit.get("description", "No Snippet")
            snippets.append(
                f"{count+1}. Title: {title}\nURL: {link}\nSnippet: {description}"
            )

        return "\n\n".join(snippets)
    except Exception as e:
        return f"Error contacting You.com API: {e}"


@tool
def scrape_webpage(url: str, max_chars: int = 5000) -> str:
    """Fetches and extracts the main text content from a given URL.
    Use this when you need the full content of a specific page discovered
    via web search, not just a snippet.

    Args:
        url: The full URL to fetch and extract text from.
        max_chars: Maximum characters to return (default 5000).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return (
            "ERROR: beautifulsoup4 is not installed. "
            "Run: pip install beautifulsoup4"
        )

    try:
        headers = {"User-Agent": "ResearchSwarm/1.0 (Academic Research Bot)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove non-content elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Extract main text
        text = soup.get_text(separator="\n", strip=True)

        # Truncate if needed
        if len(text) > max_chars:
            text = (
                text[:max_chars]
                + f"\n\n[... truncated at {max_chars} chars. "
                f"Full page is {len(text)} chars.]"
            )

        return f"Content from {url}:\n\n{text}"

    except Exception as e:
        return f"Error scraping {url}: {e}"


# ═══════════════════════════════════════════════════════
# KNOWLEDGE BASE TOOL (Bridges ingest.py → LangGraph)
# ═══════════════════════════════════════════════════════


def _get_active_agent_names() -> list[str]:
    """Return KB folders for personas currently configured in swarm_config.yml."""
    try:
        from automation.config import load_config

        config = load_config()
        agent_names = []
        for persona in config.get("personas", []):
            agent_name = Path(persona.get("persona_file", "")).parent.name
            if agent_name and agent_name not in agent_names:
                agent_names.append(agent_name)
        if agent_names:
            return agent_names
    except Exception:
        pass

    agents_dir = os.path.join(os.path.dirname(__file__), "..", "agents")
    return [
        d
        for d in os.listdir(agents_dir)
        if os.path.isdir(os.path.join(agents_dir, d)) and d != "__pycache__"
    ]


@tool
def search_knowledge_base(query: str, agent_name: str = "all", top_k: int = 5) -> str:
    """Searches the local Knowledge Base (vectorized documents in agents/*/KB/)
    for semantically relevant passages.

    Use this BEFORE external searches to check if the answer already
    exists in your local documents.

    Args:
        query: The search query to find relevant passages.
        agent_name: Search a specific agent's KB (e.g., 'ClinicalPsych') or 'all'.
        top_k: Number of top results to return.
    """
    try:
        from langchain_community.embeddings import SentenceTransformerEmbeddings
        from langchain_community.vectorstores import Chroma
    except ImportError:
        return (
            "ERROR: Required packages not installed. "
            "Run: pip install chromadb sentence-transformers"
        )

    db_base = os.path.join(os.path.dirname(__file__), "db")
    if not os.path.exists(db_base):
        return (
            "No Knowledge Base found. Run 'python -m automation.ingest' first "
            "to vectorize documents from agents/*/KB/ folders."
        )

    try:
        embedding_fn = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    except Exception as e:
        return f"Error initializing embeddings model: {e}"

    results = []

    if agent_name == "all":
        agent_names = _get_active_agent_names()
    else:
        agent_names = [agent_name]

    for name in agent_names:
        persist_dir = os.path.join(db_base, name)
        if not os.path.exists(persist_dir):
            continue
        try:
            db = Chroma(
                persist_directory=persist_dir, embedding_function=embedding_fn
            )
            docs = db.similarity_search(query, k=top_k)
            for doc in docs:
                source = doc.metadata.get("source", "Unknown")
                results.append(
                    f"[{name} KB | {os.path.basename(source)}]: "
                    f"{doc.page_content[:500]}"
                )
        except Exception as e:
            results.append(f"[{name} KB]: Error searching — {e}")

    if not results:
        return (
            "No relevant documents found in the local Knowledge Base. "
            "Try an external search tool instead."
        )

    return "\n\n---\n\n".join(results[:top_k])


# ═══════════════════════════════════════════════════════
# VERSION CONTROL TOOL (Audit Trail)
# ═══════════════════════════════════════════════════════


@tool
def git_commit_snapshot(message: str) -> str:
    """Creates a git commit of swarm output files only (Drafts/ directory and the
    Knowledge Traceability Matrix). Stages only known safe paths — never the full
    working tree — to prevent accidentally committing credentials or binaries.

    Use this after write_manuscript_section to lock in a versioned audit snapshot.

    Args:
        message: Descriptive commit message summarizing what was produced.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Determine safe staging paths from config (fall back to defaults)
    try:
        from automation.config import load_config
        cfg = load_config()
        output_dir = cfg["swarm"].get("output_dir", "./Drafts").lstrip("./")
        matrix = cfg["swarm"].get(
            "traceability_matrix", "./Knowledge_Traceability_Matrix.md"
        ).lstrip("./")
    except Exception:
        output_dir = "Drafts"
        matrix = "Knowledge_Traceability_Matrix.md"

    safe_paths = [output_dir, matrix]

    try:
        # Stage only the swarm's output paths — never git add -A
        subprocess.run(
            ["git", "add", "--", *safe_paths],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )

        status = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        if not status.stdout.strip():
            return "No changes to commit in swarm output paths."

        result = subprocess.run(
            ["git", "commit", "-m", f"[swarm-auto] {message}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )

        return f"SUCCESS: Committed snapshot.\n{result.stdout}"

    except subprocess.CalledProcessError as e:
        return f"Git commit failed: {e.stderr}"
    except FileNotFoundError:
        return "ERROR: git is not installed or not in PATH."
