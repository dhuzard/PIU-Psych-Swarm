from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from automation.config import load_config

console = Console()


@dataclass
class ValidationIssue:
    severity: str
    message: str
    path: str = ""


@dataclass
class SwarmDoctorReport:
    root_dir: Path
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def ok(self) -> bool:
        return self.error_count == 0


def inspect_swarm(root_dir: Path) -> SwarmDoctorReport:
    report = SwarmDoctorReport(root_dir=root_dir)
    config_path = root_dir / "swarm_config.yml"
    if not config_path.exists():
        report.issues.append(ValidationIssue("error", "swarm_config.yml is missing", str(config_path)))
        return report

    try:
        config = load_config(config_path)
    except Exception as e:
        report.issues.append(ValidationIssue("error", f"failed to load config: {e}", str(config_path)))
        return report

    personas = config.get("personas", [])
    tools = config.get("tools", {})
    persona_names = {persona.get("name", "") for persona in personas}

    orchestrator = config.get("orchestrator", {}).get("agent")
    journalist = config.get("orchestrator", {}).get("journalist")
    if orchestrator not in persona_names:
        report.issues.append(ValidationIssue("error", "orchestrator agent is not defined in personas", "swarm_config.yml"))
    if journalist not in persona_names:
        report.issues.append(ValidationIssue("error", "journalist agent is not defined in personas", "swarm_config.yml"))

    seen_names = set()
    seen_paths = set()
    for persona in personas:
        persona_name = persona.get("name", "")
        persona_file = persona.get("persona_file", "")
        if persona_name in seen_names:
            report.issues.append(ValidationIssue("error", f"duplicate persona name: {persona_name}", "swarm_config.yml"))
        seen_names.add(persona_name)

        persona_path = root_dir / persona_file.replace("./", "") if persona_file else None
        if not persona_file:
            report.issues.append(ValidationIssue("error", f"persona '{persona_name}' is missing persona_file", "swarm_config.yml"))
            continue

        if persona_file in seen_paths:
            report.issues.append(ValidationIssue("error", f"duplicate persona_file path: {persona_file}", "swarm_config.yml"))
        seen_paths.add(persona_file)

        if not persona_path.exists():
            report.issues.append(ValidationIssue("error", f"persona file missing for '{persona_name}'", str(persona_path)))
        kb_dir = persona_path.parent / "KB"
        if not kb_dir.exists():
            report.issues.append(ValidationIssue("warning", f"KB directory missing for '{persona_name}'", str(kb_dir)))

        persona_tools = persona.get("tools", [])
        if not persona_tools:
            report.issues.append(ValidationIssue("warning", f"persona '{persona_name}' has no tools", "swarm_config.yml"))
        for tool_name in persona_tools:
            if tool_name not in tools:
                report.issues.append(ValidationIssue("error", f"persona '{persona_name}' references unknown tool '{tool_name}'", "swarm_config.yml"))

    for tool_name, spec in tools.items():
        module_path = spec.get("module", "")
        function_name = spec.get("function", "")
        if not module_path or not function_name:
            report.issues.append(ValidationIssue("error", f"tool '{tool_name}' is missing module/function", "swarm_config.yml"))
            continue
        try:
            module = importlib.import_module(module_path)
            getattr(module, function_name)
        except Exception as e:
            report.issues.append(ValidationIssue("error", f"tool '{tool_name}' failed to import: {e}", "swarm_config.yml"))

    env_key = config.get("model", {}).get("env_key", "OPENAI_API_KEY")
    if not os.getenv(env_key):
        report.issues.append(ValidationIssue("warning", f"model env key '{env_key}' is not set in the current shell", ".env"))

    return report


def apply_safe_fixes(root_dir: Path) -> list[Path]:
    config = load_config(root_dir / "swarm_config.yml")
    created: list[Path] = []
    for persona in config.get("personas", []):
        persona_file = persona.get("persona_file", "")
        if not persona_file:
            continue
        persona_path = root_dir / persona_file.replace("./", "")
        kb_dir = persona_path.parent / "KB"
        if not kb_dir.exists():
            kb_dir.mkdir(parents=True, exist_ok=True)
            created.append(kb_dir)
        gitkeep = kb_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
            created.append(gitkeep)
    return created


def render_doctor_report(report: SwarmDoctorReport) -> None:
    status = "Healthy" if report.ok else "Problems Found"
    console.print(Panel.fit(f"[bold]{status}[/bold]\nRoot: {report.root_dir}", title="Swarm Doctor"))
    table = Table(title="Checks")
    table.add_column("Severity")
    table.add_column("Message")
    table.add_column("Path")
    if not report.issues:
        table.add_row("ok", "No issues detected", "")
    else:
        for issue in report.issues:
            table.add_row(issue.severity, issue.message, issue.path)
    console.print(table)


def preview_existing_swarm(root_dir: Path) -> None:
    config = load_config(root_dir / "swarm_config.yml")

    console.print(Panel.fit(
        f"[bold]{config['swarm']['name']}[/bold]\n"
        f"{config['swarm'].get('description', '')}\n\n"
        f"Model: {config['model']['provider']}/{config['model']['name']}\n"
        f"Orchestrator: {config.get('orchestrator', {}).get('agent', '')}\n"
        f"Journalist: {config.get('orchestrator', {}).get('journalist', '')}",
        title="Current Swarm",
    ))

    persona_table = Table(title="Personas")
    persona_table.add_column("Name")
    persona_table.add_column("Role")
    persona_table.add_column("File")
    persona_table.add_column("Tools")
    for persona in config.get("personas", []):
        persona_table.add_row(
            persona.get("name", ""),
            persona.get("role", ""),
            persona.get("persona_file", ""),
            ", ".join(persona.get("tools", [])),
        )
    console.print(persona_table)

    tool_table = Table(title="Tool Registry")
    tool_table.add_column("Key")
    tool_table.add_column("Target")
    tool_table.add_column("Description")
    for tool_name, spec in config.get("tools", {}).items():
        tool_table.add_row(
            tool_name,
            f"{spec.get('module', '')}.{spec.get('function', '')}",
            spec.get("description", ""),
        )
    console.print(tool_table)