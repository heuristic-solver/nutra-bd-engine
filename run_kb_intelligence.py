"""
run_kb_intelligence.py — Full KB Execution, Quality Audit & Fault Resolver
company_info
"""

from __future__ import annotations
import os
import sys
import io
import time
import json
from collections import Counter
from typing import List, Dict, Any

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn

from company_info.models import CompanyProfile, MovementType, FundingRoundType, MovementCategory, CompanyIntelligenceReport
from company_info.pipeline import get_kb_loader, CompanyIntelligenceEngine
from company_info.exporters import CSVExporter, JSONExporter, MarkdownReporter

console = Console(safe_box=True)


def run_full_kb_pipeline(
    limit: int = 0,
    workers: int = 8,
    output_dir: str = "company_info_output/kb_full",
) -> List[CompanyIntelligenceReport]:
    """
    Executes the 360-degree intelligence pipeline across the entire nutraceutical KB.
    """
    os.makedirs(output_dir, exist_ok=True)
    checkpoint_file = os.path.join(output_dir, "checkpoint_kb_full.jsonl")

    kb = get_kb_loader()
    all_companies = kb.get_all()
    if limit > 0:
        all_companies = all_companies[:limit]

    console.print(Panel.fit(
        f"[bold cyan]Launching Full Nutraceutical Knowledge Base Intelligence Harvester[/bold cyan]\n"
        f"[bold white]Total Companies:[/bold white] {len(all_companies)} | [bold white]Workers:[/bold white] {workers}\n"
        f"[bold white]Architecture:[/bold white] 100% Zero Paid APIs (Google News RSS + DDG + Bing + EDGAR + Web Crawling)\n"
        f"[bold white]Checkpoint File:[/bold white] {checkpoint_file}\n"
        f"[bold white]Output Directory:[/bold white] {output_dir}",
        title="[RUNNER] Full KB Intelligence Engine"
    ))

    engine = CompanyIntelligenceEngine(max_workers=workers)

    start_time = time.time()
    reports: List[CompanyIntelligenceReport] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Harvesting intelligence...", total=len(all_companies))

        def on_prog(done, total, last_name):
            progress.update(
                task,
                completed=done,
                description=f"[cyan]Scanned {done}/{total} ({last_name[:20]}...)"
            )

        reports = engine.scan_batch(
            all_companies,
            checkpoint_file=checkpoint_file,
            resume=True,
            on_progress=on_prog,
        )

    elapsed_sec = round(time.time() - start_time, 2)
    console.print(f"\n[bold green]Scan Completed in {elapsed_sec}s! Processed {len(reports)} companies.[/bold green]\n")

    # -----------------------------------------------------------------------
    # Export All Datasets
    # -----------------------------------------------------------------------
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

    console.print(f"[bold white]Exported Segregated Datasets:[/bold white]")
    console.print(f"  • Master Overview: [cyan]{master_csv}[/cyan]")
    console.print(f"  • Role Changes: [cyan]{roles_csv}[/cyan]")
    console.print(f"  • Funding Events: [cyan]{funding_csv}[/cyan]")
    console.print(f"  • Strategic Movements: [cyan]{movements_csv}[/cyan]")
    console.print(f"  • Markdown Executive Briefing: [cyan]{master_md}[/cyan]")
    console.print(f"  • JSON Master File: [cyan]{master_json}[/cyan]\n")

    return reports


def audit_intelligence_results(reports: List[CompanyIntelligenceReport], output_dir: str = "company_info_output/kb_full") -> Dict[str, Any]:
    """
    Performs comprehensive statistical, precision, and quality auditing on the extracted intelligence.
    """
    total_companies = len(reports)
    companies_with_signals = [r for r in reports if r.total_signals_discovered > 0]
    companies_with_roles = [r for r in reports if len(r.role_changes) > 0]
    companies_with_funding = [r for r in reports if len(r.funding_events) > 0]
    companies_with_movements = [r for r in reports if len(r.strategic_movements) > 0]

    all_roles = [r for rep in reports for r in rep.role_changes]
    all_funding = [f for rep in reports for f in rep.funding_events]
    all_movements = [m for rep in reports for m in rep.strategic_movements]

    joined_roles = [r for r in all_roles if r.movement_type in (MovementType.JOINED, MovementType.PROMOTED, MovementType.BOARD_APPOINTMENT)]
    departed_roles = [r for r in all_roles if r.movement_type == MovementType.DEPARTED]

    total_funding_volume_usd = sum(f.amount_usd or 0.0 for f in all_funding)

    # Category counts
    role_movement_dist = Counter(r.movement_type.value for r in all_roles)
    funding_round_dist = Counter(f.round_type.value for f in all_funding)
    movement_cat_dist = Counter(m.category.value for m in all_movements)

    # Segment performance
    segment_counts: Dict[str, Dict[str, int]] = {}
    for r in reports:
        seg = r.profile.specialty or "General / Uncategorized"
        if seg not in segment_counts:
            segment_counts[seg] = {"total": 0, "with_signals": 0, "roles": 0, "funding": 0, "movements": 0}
        segment_counts[seg]["total"] += 1
        if r.total_signals_discovered > 0:
            segment_counts[seg]["with_signals"] += 1
        segment_counts[seg]["roles"] += len(r.role_changes)
        segment_counts[seg]["funding"] += len(r.funding_events)
        segment_counts[seg]["movements"] += len(r.strategic_movements)

    # Print Rich Summary Tables
    console.print(Panel.fit("[bold green]Comprehensive Intelligence Audit & Statistical Analysis[/bold green]", title="[AUDIT] Quality & Quantity"))

    t_metrics = Table(title="Overall Knowledge Base Coverage & Yield", show_header=True, header_style="bold cyan")
    t_metrics.add_column("Metric", style="bold")
    t_metrics.add_column("Count / Value", style="bold yellow")
    t_metrics.add_column("Percentage", style="bold green")

    t_metrics.add_row("Total Companies in KB", str(total_companies), "100.0%")
    t_metrics.add_row("Companies with Active Signals", str(len(companies_with_signals)), f"{(len(companies_with_signals)/max(1, total_companies))*100:.1f}%")
    t_metrics.add_row("Companies with Role Changes", str(len(companies_with_roles)), f"{(len(companies_with_roles)/max(1, total_companies))*100:.1f}%")
    t_metrics.add_row("Companies with Funding Rounds", str(len(companies_with_funding)), f"{(len(companies_with_funding)/max(1, total_companies))*100:.1f}%")
    t_metrics.add_row("Companies with Strategic Movements", str(len(companies_with_movements)), f"{(len(companies_with_movements)/max(1, total_companies))*100:.1f}%")
    t_metrics.add_row("Total People Joined / Promoted", str(len(joined_roles)), "-")
    t_metrics.add_row("Total People Departed", str(len(departed_roles)), "-")
    t_metrics.add_row("Total Strategic Milestones (M&A/Plants/Launches)", str(len(all_movements)), "-")
    t_metrics.add_row("Total Tracked Capital Raised (USD)", f"${total_funding_volume_usd:,.2f}", "-")
    console.print(t_metrics)
    console.print()

    # Role movement breakdown
    t_role_dist = Table(title="Personnel Movement Breakdown (Joined vs Departed vs Promoted)", show_header=True, header_style="bold magenta")
    t_role_dist.add_column("Movement Type", style="bold")
    t_role_dist.add_column("Count", style="bold yellow")
    t_role_dist.add_column("Share %", style="bold cyan")
    for m_type, count in role_movement_dist.most_common():
        share = (count / max(1, len(all_roles))) * 100
        t_role_dist.add_row(m_type, str(count), f"{share:.1f}%")
    console.print(t_role_dist)
    console.print()

    # Strategic movements breakdown
    t_mov_dist = Table(title="Strategic Corporate Movement Breakdown", show_header=True, header_style="bold blue")
    t_mov_dist.add_column("Category", style="bold")
    t_mov_dist.add_column("Count", style="bold yellow")
    t_mov_dist.add_column("Share %", style="bold cyan")
    for m_cat, count in movement_cat_dist.most_common():
        share = (count / max(1, len(all_movements))) * 100
        t_mov_dist.add_row(m_cat, str(count), f"{share:.1f}%")
    console.print(t_mov_dist)
    console.print()

    # Audit Report JSON export
    audit_data = {
        "total_companies_scanned": total_companies,
        "companies_with_signals": len(companies_with_signals),
        "companies_with_roles": len(companies_with_roles),
        "companies_with_funding": len(companies_with_funding),
        "companies_with_movements": len(companies_with_movements),
        "total_roles_captured": len(all_roles),
        "total_people_joined": len(joined_roles),
        "total_people_departed": len(departed_roles),
        "total_funding_events": len(all_funding),
        "total_funding_usd": total_funding_volume_usd,
        "total_strategic_movements": len(all_movements),
        "role_distribution": dict(role_movement_dist),
        "funding_distribution": dict(funding_round_dist),
        "movement_distribution": dict(movement_cat_dist),
    }

    audit_json_path = os.path.join(output_dir, "intelligence_audit_summary.json")
    with open(audit_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    console.print(f"[bold green]Audit Summary Saved to:[/bold green] [cyan]{audit_json_path}[/cyan]\n")
    return audit_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Full Nutraceutical KB Intelligence Harvester & Auditor")
    parser.add_argument("--limit", type=int, default=0, help="Number of companies to scan (0 = all 1,018)")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel worker threads")
    parser.add_argument("--output-dir", type=str, default="company_info_output/kb_full", help="Output directory")
    args = parser.parse_args()

    reports = run_full_kb_pipeline(limit=args.limit, workers=args.workers, output_dir=args.output_dir)
    audit_intelligence_results(reports, output_dir=args.output_dir)
