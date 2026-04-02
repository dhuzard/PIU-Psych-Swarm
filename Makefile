.PHONY: setup run ingest info scaffold test clean help

# ═══════════════════════════════════════════════════════
# Research Swarm — Makefile
# ═══════════════════════════════════════════════════════

VENV     = .venv
PYTHON   = $(VENV)/Scripts/python
PIP      = $(VENV)/Scripts/pip
ACTIVATE = $(VENV)/Scripts/activate

# ── Help (default) ───────────────────────────────────
help:
	@echo.
	@echo   Research Swarm — Available Commands
	@echo   ===================================
	@echo   make setup       Create venv, install deps, copy .env.example
	@echo   make run         Run the swarm (set PROMPT="your prompt")
	@echo   make ingest      Vectorize documents from agents/*/KB/ folders
	@echo   make info        Display the current swarm configuration
	@echo   make scaffold    Scaffold a new domain (set DOMAIN="your domain")
	@echo   make test        Run the test suite
	@echo   make clean       Remove venv and cached files
	@echo.

# ── Setup ────────────────────────────────────────────
setup:
	@echo 🔧 Creating virtual environment...
	python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@if not exist .env (copy .env.example .env & echo ✅ .env created from .env.example) else (echo ⏭️  .env already exists)
	@echo.
	@echo ✅ Setup complete!
	@echo    1. Edit .env with your API keys
	@echo    2. Run: make info       (check your config)
	@echo    3. Run: make run PROMPT="Your first research prompt"

# ── Run ──────────────────────────────────────────────
run:
ifndef PROMPT
	@echo ERROR: Please provide a prompt.
	@echo Usage: make run PROMPT="Search for the latest FDA guidance on NAMs"
	@exit /b 1
endif
	$(PYTHON) -m automation.main execute "$(PROMPT)"

# ── Ingest KB Documents ──────────────────────────────
ingest:
	@echo 📚 Vectorizing Knowledge Base documents...
	$(PYTHON) -m automation.ingest

# ── Info ─────────────────────────────────────────────
info:
	$(PYTHON) -m automation.main info

# ── Scaffold ─────────────────────────────────────────
scaffold:
ifndef DOMAIN
	@echo ERROR: Please provide a domain name.
	@echo Usage: make scaffold DOMAIN="Climate Science"
	@exit /b 1
endif
	$(PYTHON) -m automation.main scaffold "$(DOMAIN)"

# ── Test ─────────────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/ -v

# ── Clean ────────────────────────────────────────────
clean:
	@echo 🧹 Cleaning up...
	@if exist $(VENV) rmdir /s /q $(VENV)
	@if exist automation\__pycache__ rmdir /s /q automation\__pycache__
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist automation\db rmdir /s /q automation\db
	@echo ✅ Cleaned.
