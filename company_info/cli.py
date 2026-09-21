"""
cli.py — Rich Command-Line Interface for Company Intelligence
company_info
"""

from __future__ import annotations
import os
import sys
import io
import argparse
from typing import List

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from company_info.models import CompanyProfile, MovementType
from company_info.pipeline import NutraceuticalKBLoader, get_kb_loader, CompanyIntelligenceEngine
from company_info.exporters import CSVExporter, JSONExporter, MarkdownReporter

console = Console(safe_box=True)


def scan_single_company(company_name: str, domain: str = None, output_prefix: str = None) -> None:
    """Scans an individual company and prints a rich terminal brief."""
    kb = get_kb_loader()
    profile = kb.find_by_name(company_name)

    if not profile:
        profile = CompanyProfile(
            company_name=company_name,
            domain=domain or company_name.lower().replace(" ", "") + ".com",
        )

    console.print(Panel.fit(
        f"[bold cyan]Scanning Company Intelligence (100% Zero Paid APIs)[/bold cyan]\n"
        f"[bold white]Company:[/bold white] {profile.company_name} | [bold white]Domain:[/bold white] {profile.domain or 'N/A'}\n"
        f"[bold white]Specialty:[/bold white] {profile.specialty or 'N/A'} | [bold white]HQ:[/bold white] {profile.headquarters or 'N/A'}",
        title="[SEARCH] Company Info Engine"
    ))

    engine = CompanyIntelligenceEngine()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"[green]Aggregating open intelligence for {profile.company_name}...", total=None)
        report = engine.scan_company(profile)
        progress.update(task, completed=100)

    console.print(f"\n[bold green]Scan Complete in {report.execution_time_sec}s! Discovered {report.total_signals_discovered} signals.[/bold green]\n")

    # 1. Role Changes & Personnel
    t_roles = Table(title="[ROLES] Role Changes & Personnel Movements", show_header=True, header_style="bold magenta")
    t_roles.add_column("Movement", style="bold")
    t_roles.add_column("Person Name", style="bold cyan")
    t_roles.add_column("Role Title", style="white")
    t_roles.add_column("Date", style="dim")
    t_roles.add_column("Source", style="dim blue")

    if report.role_changes:
        for r in report.role_changes:
            style = "green" if r.movement_type == MovementType.JOINED else ("red" if r.movement_type == MovementType.DEPARTED else "blue")
            t_roles.add_row(f"[{style}]{r.movement_type.value}[/{style}]", r.person_name, r.role_title, r.date_str or "Recent", r.source_name or "Web")
        console.print(t_roles)
    else:
        console.print("[dim]No role changes detected.[/dim]\n")

    # 2. Funding
    t_fund = Table(title="[FUNDING] Funding & Capital Events", show_header=True, header_style="bold green")
    t_fund.add_column("Round Type", style="bold")
    t_fund.add_column("Amount", style="bold yellow")
    t_fund.add_column("Lead Investors", style="cyan")
    t_fund.add_column("Date", style="dim")
    t_fund.add_column("Source", style="dim blue")

    if report.funding_events:
        for f in report.funding_events:
            invs = ", ".join(f.lead_investors) if f.lead_investors else "Undisclosed"
            t_fund.add_row(f.round_type.value, f.amount_raw or "Undisclosed", invs, f.date_str or "Recent", f.source_name or "Web")
        console.print(t_fund)
    else:
        console.print("[dim]No funding events detected.[/dim]\n")

    # 3. Strategic Movements
    t_mov = Table(title="[MOVEMENTS] Strategic Movements & Milestones", show_header=True, header_style="bold cyan")
    t_mov.add_column("Category", style="bold")
    t_mov.add_column("Headline", style="white")
    t_mov.add_column("Date", style="dim")
    t_mov.add_column("Source", style="dim blue")

    if report.strategic_movements:
        for m in report.strategic_movements:
            t_mov.add_row(m.category.value, m.headline[:70] + "...", m.date_str or "Recent", m.source_name or "Web")
        console.print(t_mov)
    else:
        console.print("[dim]No strategic movements detected.[/dim]\n")

    # Optional Exports
    if output_prefix:
        os.makedirs(os.path.dirname(output_prefix) if os.path.dirname(output_prefix) else ".", exist_ok=True)
        CSVExporter.export_master_summary([report], f"{output_prefix}_master.csv")
        CSVExporter.export_role_changes([report], f"{output_prefix}_roles.csv")
        CSVExporter.export_funding_events([report], f"{output_prefix}_funding.csv")
        CSVExporter.export_strategic_movements([report], f"{output_prefix}_movements.csv")
        MarkdownReporter.export([report], f"{output_prefix}_brief.md")
        console.print(f"[bold green]Saved segregated reports to {output_prefix}_*.csv and .md[/bold green]")


def scan_knowledge_base(
    limit: int = 10,
    segment: str = None,
    specialty: str = None,
    workers: int = 6,
    output_dir: str = "company_info_output",
    checkpoint: str = None,
) -> None:
    """Batch scans a cohort of nutraceutical companies from the knowledge base."""
    kb = get_kb_loader()
    candidates: List[CompanyProfile] = []

    if segment:
        candidates = kb.filter_by_segment(segment)
    elif specialty:
        candidates = kb.filter_by_specialty(specialty)
    else:
        candidates = kb.get_all()

    cohort = candidates[:limit] if limit > 0 else candidates
    checkpoint_file = checkpoint or os.path.join(output_dir, "checkpoint_kb.jsonl")

    console.print(Panel.fit(
        f"[bold cyan]Batch Scanning {len(cohort)} Nutraceutical KB Companies (100% Zero Paid APIs)[/bold cyan]\n"
        f"[bold white]Segment Filter:[/bold white] {segment or 'All'} | [bold white]Specialty Filter:[/bold white] {specialty or 'All'}\n"
        f"[bold white]Parallel Workers:[/bold white] {workers} | [bold white]Checkpoint File:[/bold white] {checkpoint_file}\n"
        f"[bold white]Output Directory:[/bold white] {output_dir}",
        title="[BATCH] Batch Intelligence Harvester"
    ))

    os.makedirs(output_dir, exist_ok=True)
    engine = CompanyIntelligenceEngine(max_workers=workers)

    reports = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Scanning companies...", total=len(cohort))

        def on_prog(done, total, last_name):
            progress.update(task, completed=done, description=f"[cyan]Processed {done}/{total}: {last_name[:25]}")

        reports = engine.scan_batch(
            cohort,
            checkpoint_file=checkpoint_file,
            resume=True,
            on_progress=on_prog,
        )

    # Export datasets
    master_csv = os.path.join(output_dir, "company_intelligence_master.csv")
    roles_csv = os.path.join(output_dir, "company_role_changes.csv")
    funding_csv = os.path.join(output_dir, "company_funding_rounds.csv")
    movements_csv = os.path.join(output_dir, "company_strategic_movements.csv")
    master_md = os.path.join(output_dir, "company_intelligence_report.md")
    master_json = os.path.join(output_dir, "company_intelligence.json")

    CSVExporter.export_master_summary(reports, master_csv)
    CSVExporter.export_role_changes(reports, roles_csv)
    CSVExporter.export_funding_events(reports, funding_csv)
    CSVExporter.export_strategic_movements(reports, movements_csv)
    MarkdownReporter.export(reports, master_md)
    JSONExporter.export(reports, master_json)

    console.print(f"\n[bold green]Batch Complete! Scanned {len(reports)} companies.[/bold green]")
    console.print(f"  * Master Overview: [cyan]{master_csv}[/cyan]")
    console.print(f"  * Role Changes: [cyan]{roles_csv}[/cyan]")
    console.print(f"  * Funding Rounds: [cyan]{funding_csv}[/cyan]")
    console.print(f"  * Strategic Movements: [cyan]{movements_csv}[/cyan]")
    console.print(f"  * Markdown Brief: [cyan]{master_md}[/cyan]")


def main():
    parser = argparse.ArgumentParser(description="Zero-Cost Custom Company Intelligence Scraper CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # scan command
    p_scan = subparsers.add_parser("scan", help="Scan a single company")
    p_scan.add_argument("company", type=str, help="Company name (e.g. 'Thorne', 'Ritual')")
    p_scan.add_argument("--domain", type=str, default=None, help="Company official domain (optional)")
    p_scan.add_argument("--output", type=str, default=None, help="Output file prefix (e.g. 'reports/thorne')")

    # batch-kb command
    p_batch = subparsers.add_parser("batch-kb", help="Batch scan nutraceutical KB companies")
    p_batch.add_argument("--limit", type=int, default=10, help="Number of companies to scan (0 or default for all)")
    p_batch.add_argument("--segment", type=str, default=None, help="Filter by segment (supplement_brand, ingredient_supplier, contract_manufacturer)")
    p_batch.add_argument("--specialty", type=str, default=None, help="Filter by specialty keyword")
    p_batch.add_argument("--workers", type=int, default=6, help="Parallel worker threads (default: 6)")
    p_batch.add_argument("--checkpoint", type=str, default=None, help="Custom path for streaming checkpoint JSONL")
    p_batch.add_argument("--output-dir", type=str, default="company_info_output", help="Directory to save CSV & MD files")

    # search-kb command
    p_search = subparsers.add_parser("search-kb", help="Search nutraceutical knowledge base")
    p_search.add_argument("query", type=str, help="Search term (name, ingredient, or specialty)")

    args = parser.parse_args()

    if args.command == "scan":
        scan_single_company(args.company, domain=args.domain, output_prefix=args.output)
    elif args.command == "batch-kb":
        scan_knowledge_base(limit=args.limit, segment=args.segment, specialty=args.specialty, output_dir=args.output_dir)
    elif args.command == "search-kb":
        kb = get_kb_loader()
        matches = [c for c in kb.get_all() if args.query.lower() in c.company_name.lower() or (c.specialty and args.query.lower() in c.specialty.lower())]
        console.print(f"[bold cyan]Found {len(matches)} matching companies in KB for '{args.query}':[/bold cyan]")
        for m in matches[:20]:
            console.print(f"  * [bold white]{m.company_name}[/bold white] ({m.domain or 'No domain'}) - [dim]{m.specialty or 'N/A'}[/dim]")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
