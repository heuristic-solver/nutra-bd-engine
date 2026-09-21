"""
markdown_reporter.py — Executive Markdown Intelligence Briefing Generator
company_info / exporters
"""

from __future__ import annotations
from typing import List
from company_info.models.report import CompanyIntelligenceReport
from company_info.models.role_change import MovementType


class MarkdownReporter:
    """Generates structured Markdown executive briefings from intelligence reports."""

    @staticmethod
    def generate_report(report: CompanyIntelligenceReport) -> str:
        lines = []
        lines.append(f"# Executive Intelligence Brief: {report.company_name}")
        lines.append("")
        lines.append(f"**Domain:** `{report.domain or 'N/A'}` | **Headquarters:** `{report.profile.headquarters or 'N/A'}` | **Ownership:** `{report.profile.ownership or 'Private'}`")
        if report.profile.specialty:
            lines.append(f"**Specialty:** {report.profile.specialty}")
        lines.append("")
        lines.append(f"> **Scan Overview:** Discovered **{report.total_signals_discovered} total signals** across {len(report.data_sources_scraped)} open sources in {report.execution_time_sec}s.")
        lines.append("")

        # 1. Role Changes & Key Personnel
        lines.append("## 👥 Role Changes & Personnel Movements")
        lines.append("")
        if not report.role_changes:
            lines.append("_No recent role changes or executive movements detected._\n")
        else:
            lines.append("| Movement | Person Name | Role Title | Date / Recency | Source & Evidence |")
            lines.append("|---|---|---|---|---|")
            for r in report.role_changes:
                mov_badge = f"**{r.movement_type.value}**"
                if r.movement_type in (MovementType.JOINED, MovementType.PROMOTED):
                    mov_badge = f"🟢 {r.movement_type.value}"
                elif r.movement_type == MovementType.DEPARTED:
                    mov_badge = f"🔴 {r.movement_type.value}"
                else:
                    mov_badge = f"🔵 {r.movement_type.value}"

                src_link = f"[{r.source_name or 'Source'}]({r.source_url})" if r.source_url else (r.source_name or "N/A")
                date_str = r.date_str or "Recent"
                lines.append(f"| {mov_badge} | **{r.person_name}** | {r.role_title} | {date_str} | {src_link} |")
            lines.append("")

        # 2. Funding & Investments
        lines.append("## 💰 Funding Rounds & Capital Structure")
        lines.append("")
        if not report.funding_events:
            lines.append("_No recent venture funding, private equity, or debt events detected._\n")
        else:
            lines.append("| Round Type | Amount | Lead Investors | Date | Announcement |")
            lines.append("|---|---|---|---|---|")
            for f in report.funding_events:
                amt = f"**{f.amount_raw or 'Undisclosed'}**"
                invs = ", ".join(f.lead_investors) if f.lead_investors else "Undisclosed"
                date_str = f.date_str or "Recent"
                src_link = f"[{f.announcement_title[:50]}...]({f.source_url})" if f.source_url else f.announcement_title[:50]
                lines.append(f"| {f.round_type.value} | {amt} | {invs} | {date_str} | {src_link} |")
            lines.append("")

        # 3. Strategic Company Movements
        lines.append("## 🚀 Strategic Movements & Milestones")
        lines.append("")
        if not report.strategic_movements:
            lines.append("_No recent M&A, facility expansions, or strategic partnerships detected._\n")
        else:
            lines.append("| Category | Headline | Summary | Date | Source |")
            lines.append("|---|---|---|---|---|")
            for m in report.strategic_movements:
                src_link = f"[{m.source_name or 'Source'}]({m.source_url})" if m.source_url else "N/A"
                date_str = m.date_str or "Recent"
                lines.append(f"| **{m.category.value}** | {m.headline} | {m.summary[:100]}... | {date_str} | {src_link} |")
            lines.append("")

        # 4. Sources Scraped
        lines.append("---")
        lines.append(f"**Data Sources Consulted (Zero Paid APIs):** {', '.join(report.data_sources_scraped)}")
        lines.append("")

        return "\n".join(lines)

    @classmethod
    def export(cls, reports: List[CompanyIntelligenceReport], filepath: str) -> None:
        all_md = "\n\n---\n\n".join(cls.generate_report(r) for r in reports)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(all_md)
