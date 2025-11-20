#!/usr/bin/env python3
"""
Storage Volume Simulation for Email Platform
Calculates storage requirements for different email volumes and time periods.
"""

from dataclasses import dataclass
from typing import Dict, List
import json


@dataclass
class EmailTypeSizes:
    """Average sizes for different email types (in KB)"""
    # Text-only email
    text_body: float = 3.0          # Plain text body

    # HTML email (newsletter, formatted)
    html_small: float = 25.0        # Simple HTML
    html_medium: float = 75.0       # Newsletter with images (inline base64)
    html_large: float = 150.0       # Complex HTML newsletter

    # Metadata (always stored)
    metadata: float = 2.0           # subject, sender, timestamps, category, confidence, etc.

    # Summary (LLM-generated, 2-3 sentences)
    summary: float = 0.5

    # Attachments (stored separately in attachments table)
    attachment_small: float = 100.0  # PDF document
    attachment_medium: float = 500.0 # Spreadsheet
    attachment_large: float = 2000.0 # Presentation/Images


@dataclass
class EmailDistribution:
    """Distribution of email types (percentages must sum to 100)"""
    text_only: float = 30.0          # Simple text emails
    html_simple: float = 40.0        # HTML emails without heavy content
    html_newsletter: float = 20.0    # Newsletters with images
    html_complex: float = 5.0        # Complex HTML (rare)
    with_small_attachment: float = 3.0
    with_medium_attachment: float = 1.5
    with_large_attachment: float = 0.5

    def validate(self):
        total = (self.text_only + self.html_simple + self.html_newsletter +
                 self.html_complex + self.with_small_attachment +
                 self.with_medium_attachment + self.with_large_attachment)
        assert abs(total - 100.0) < 0.1, f"Distribution must sum to 100%, got {total}%"


def calculate_email_size(storage_level: str, sizes: EmailTypeSizes) -> Dict[str, float]:
    """
    Calculate average email size for different types and storage levels.
    Returns dict of {email_type: size_in_kb}
    """
    dist = EmailDistribution()
    dist.validate()

    result = {}

    if storage_level == 'full':
        # Store everything: body_text + body_html + summary + metadata
        result['text_only'] = sizes.metadata + sizes.text_body + sizes.summary
        result['html_simple'] = sizes.metadata + sizes.text_body + sizes.html_small + sizes.summary
        result['html_newsletter'] = sizes.metadata + sizes.text_body + sizes.html_medium + sizes.summary
        result['html_complex'] = sizes.metadata + sizes.text_body + sizes.html_large + sizes.summary
        result['with_small_attachment'] = (sizes.metadata + sizes.text_body + sizes.html_small +
                                           sizes.summary + sizes.attachment_small)
        result['with_medium_attachment'] = (sizes.metadata + sizes.text_body + sizes.html_small +
                                            sizes.summary + sizes.attachment_medium)
        result['with_large_attachment'] = (sizes.metadata + sizes.text_body + sizes.html_small +
                                           sizes.summary + sizes.attachment_large)

    elif storage_level == 'summary':
        # Store only: summary + metadata (no body)
        result['text_only'] = sizes.metadata + sizes.summary
        result['html_simple'] = sizes.metadata + sizes.summary
        result['html_newsletter'] = sizes.metadata + sizes.summary
        result['html_complex'] = sizes.metadata + sizes.summary
        # Attachments metadata still stored, but not the file
        result['with_small_attachment'] = sizes.metadata + sizes.summary + 1.0  # attachment metadata
        result['with_medium_attachment'] = sizes.metadata + sizes.summary + 1.0
        result['with_large_attachment'] = sizes.metadata + sizes.summary + 1.0

    elif storage_level == 'minimal':
        # Store only: metadata
        result['text_only'] = sizes.metadata
        result['html_simple'] = sizes.metadata
        result['html_newsletter'] = sizes.metadata
        result['html_complex'] = sizes.metadata
        result['with_small_attachment'] = sizes.metadata + 0.5  # attachment metadata only
        result['with_medium_attachment'] = sizes.metadata + 0.5
        result['with_large_attachment'] = sizes.metadata + 0.5

    return result


def calculate_average_email_size(storage_level: str) -> float:
    """Calculate weighted average email size based on distribution"""
    dist = EmailDistribution()
    sizes = EmailTypeSizes()

    type_sizes = calculate_email_size(storage_level, sizes)

    # Weighted average
    avg_size = (
        (dist.text_only / 100.0) * type_sizes['text_only'] +
        (dist.html_simple / 100.0) * type_sizes['html_simple'] +
        (dist.html_newsletter / 100.0) * type_sizes['html_newsletter'] +
        (dist.html_complex / 100.0) * type_sizes['html_complex'] +
        (dist.with_small_attachment / 100.0) * type_sizes['with_small_attachment'] +
        (dist.with_medium_attachment / 100.0) * type_sizes['with_medium_attachment'] +
        (dist.with_large_attachment / 100.0) * type_sizes['with_large_attachment']
    )

    return avg_size


def format_size(size_kb: float) -> str:
    """Format size in human-readable format"""
    if size_kb < 1024:
        return f"{size_kb:.2f} KB"
    elif size_kb < 1024 * 1024:
        return f"{size_kb / 1024:.2f} MB"
    else:
        return f"{size_kb / (1024 * 1024):.2f} GB"


def simulate_storage(emails_per_day: int, years: int, storage_level: str) -> Dict:
    """Simulate storage requirements"""
    avg_size_kb = calculate_average_email_size(storage_level)

    days = years * 365
    total_emails = emails_per_day * days
    total_size_kb = total_emails * avg_size_kb

    # Add database overhead (indices, foreign keys, etc.) - approximately 15%
    db_overhead = total_size_kb * 0.15
    total_with_overhead_kb = total_size_kb + db_overhead

    return {
        'emails_per_day': emails_per_day,
        'years': years,
        'storage_level': storage_level,
        'total_emails': total_emails,
        'avg_email_size_kb': avg_size_kb,
        'raw_data_size_kb': total_size_kb,
        'db_overhead_kb': db_overhead,
        'total_size_kb': total_with_overhead_kb,
        'total_size_mb': total_with_overhead_kb / 1024,
        'total_size_gb': total_with_overhead_kb / (1024 * 1024),
    }


def print_breakdown():
    """Print detailed breakdown of email sizes"""
    print("=" * 80)
    print("EMAIL SIZE BREAKDOWN BY TYPE AND STORAGE LEVEL")
    print("=" * 80)

    sizes = EmailTypeSizes()
    dist = EmailDistribution()

    print("\n📊 EMAIL TYPE DISTRIBUTION (Assumed)")
    print("-" * 80)
    print(f"  Text-only emails:              {dist.text_only:>6.1f}%")
    print(f"  Simple HTML:                   {dist.html_simple:>6.1f}%")
    print(f"  HTML Newsletters:              {dist.html_newsletter:>6.1f}%")
    print(f"  Complex HTML:                  {dist.html_complex:>6.1f}%")
    print(f"  With small attachment (<100KB):{dist.with_small_attachment:>6.1f}%")
    print(f"  With medium attachment (~500KB):{dist.with_medium_attachment:>6.1f}%")
    print(f"  With large attachment (2MB+):  {dist.with_large_attachment:>6.1f}%")

    print("\n" + "=" * 80)
    print("AVERAGE EMAIL SIZE BY STORAGE LEVEL")
    print("=" * 80)

    for level in ['full', 'summary', 'minimal']:
        avg = calculate_average_email_size(level)
        print(f"\n{level.upper():>10}: {format_size(avg):>12} per email")

        type_sizes = calculate_email_size(level, sizes)
        print("  " + "-" * 76)
        for email_type, size in type_sizes.items():
            print(f"    {email_type:.<30} {format_size(size):>12}")


def print_simulation_table():
    """Print comprehensive simulation table"""
    print("\n" + "=" * 80)
    print("STORAGE SIMULATION: VOLUME REQUIREMENTS")
    print("=" * 80)

    emails_per_day_options = [10, 50, 100]
    years_options = [1, 3, 8]
    storage_levels = ['full', 'summary', 'minimal']

    for level in storage_levels:
        print(f"\n{'=' * 80}")
        print(f"STORAGE LEVEL: {level.upper()}")
        print(f"{'=' * 80}")
        print(f"\n{'Time Period →':>20}", end="")
        for years in years_options:
            print(f"{years} year{'s' if years > 1 else '':>2}  │", end="")
        print()
        print(f"{'Emails/Day ↓':>20}", end="")
        for _ in years_options:
            print(f"{'─' * 8}│", end="")
        print()

        for emails_per_day in emails_per_day_options:
            print(f"{emails_per_day:>15} emails │", end="")
            for years in years_options:
                result = simulate_storage(emails_per_day, years, level)
                size_gb = result['total_size_gb']

                if size_gb < 0.1:
                    print(f" {result['total_size_mb']:>5.1f} MB │", end="")
                else:
                    print(f" {size_gb:>5.2f} GB │", end="")

            print()


def print_tiered_simulation():
    """Simulate tiered storage strategy"""
    print("\n" + "=" * 80)
    print("TIERED STORAGE SIMULATION (Recommended Strategy)")
    print("=" * 80)
    print("\nStrategy:")
    print("  • 0-90 days:     ALL emails → storage_level='full'")
    print("  • 91-365 days:   wichtig/medium → 'full', unwichtig → 'summary'")
    print("  • 365+ days:     wichtig → 'full', medium → 'summary', unwichtig → 'minimal'")
    print("\nAssumed distribution: 20% wichtig, 30% medium, 50% unwichtig")
    print()

    emails_per_day_options = [10, 50, 100]
    years_options = [1, 3, 8]

    # Distribution by importance
    wichtig_pct = 0.20
    medium_pct = 0.30
    unwichtig_pct = 0.50

    avg_full = calculate_average_email_size('full')
    avg_summary = calculate_average_email_size('summary')
    avg_minimal = calculate_average_email_size('minimal')

    print(f"\n{'Time Period →':>20}", end="")
    for years in years_options:
        print(f"{years} year{'s' if years > 1 else '':>2}  │", end="")
    print()
    print(f"{'Emails/Day ↓':>20}", end="")
    for _ in years_options:
        print(f"{'─' * 8}│", end="")
    print()

    for emails_per_day in emails_per_day_options:
        print(f"{emails_per_day:>15} emails │", end="")

        for years in years_options:
            days_total = years * 365

            # 0-90 days: ALL full
            days_period1 = min(90, days_total)
            emails_period1 = emails_per_day * days_period1
            size_period1 = emails_period1 * avg_full

            # 91-365 days: wichtig/medium full, unwichtig summary
            days_period2 = max(0, min(365 - 90, days_total - 90))
            emails_period2 = emails_per_day * days_period2
            size_period2 = (
                emails_period2 * wichtig_pct * avg_full +
                emails_period2 * medium_pct * avg_full +
                emails_period2 * unwichtig_pct * avg_summary
            )

            # 365+ days: wichtig full, medium summary, unwichtig minimal
            days_period3 = max(0, days_total - 365)
            emails_period3 = emails_per_day * days_period3
            size_period3 = (
                emails_period3 * wichtig_pct * avg_full +
                emails_period3 * medium_pct * avg_summary +
                emails_period3 * unwichtig_pct * avg_minimal
            )

            total_size_kb = size_period1 + size_period2 + size_period3
            # Add 15% DB overhead
            total_with_overhead = total_size_kb * 1.15
            size_gb = total_with_overhead / (1024 * 1024)
            size_mb = total_with_overhead / 1024

            if size_gb < 0.1:
                print(f" {size_mb:>5.1f} MB │", end="")
            else:
                print(f" {size_gb:>5.2f} GB │", end="")

        print()


def print_comparison_summary():
    """Print comparison summary for decision making"""
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY (100 emails/day for 3 years)")
    print("=" * 80)

    emails_per_day = 100
    years = 3

    print(f"\nScenario: {emails_per_day} emails/day × {years} years = {emails_per_day * 365 * years:,} total emails")
    print()

    strategies = {
        'All FULL (simplest)': simulate_storage(100, 3, 'full'),
        'All SUMMARY': simulate_storage(100, 3, 'summary'),
        'All MINIMAL': simulate_storage(100, 3, 'minimal'),
    }

    # Calculate tiered
    wichtig_pct = 0.20
    medium_pct = 0.30
    unwichtig_pct = 0.50
    avg_full = calculate_average_email_size('full')
    avg_summary = calculate_average_email_size('summary')
    avg_minimal = calculate_average_email_size('minimal')

    days_total = years * 365
    days_period1 = min(90, days_total)
    days_period2 = max(0, min(365 - 90, days_total - 90))
    days_period3 = max(0, days_total - 365)

    emails_period1 = emails_per_day * days_period1
    emails_period2 = emails_per_day * days_period2
    emails_period3 = emails_per_day * days_period3

    size_period1 = emails_period1 * avg_full
    size_period2 = (
        emails_period2 * wichtig_pct * avg_full +
        emails_period2 * medium_pct * avg_full +
        emails_period2 * unwichtig_pct * avg_summary
    )
    size_period3 = (
        emails_period3 * wichtig_pct * avg_full +
        emails_period3 * medium_pct * avg_summary +
        emails_period3 * unwichtig_pct * avg_minimal
    )

    tiered_total_kb = (size_period1 + size_period2 + size_period3) * 1.15

    print(f"{'Strategy':<30} {'Storage Required':>20} {'vs. FULL':>15}")
    print("-" * 80)

    full_size = strategies['All FULL (simplest)']['total_size_gb']

    for name, result in strategies.items():
        size_gb = result['total_size_gb']
        savings_pct = ((full_size - size_gb) / full_size * 100) if full_size > 0 else 0
        print(f"{name:<30} {size_gb:>15.2f} GB   {savings_pct:>10.1f}% saved")

    # Print tiered
    tiered_gb = tiered_total_kb / (1024 * 1024)
    tiered_savings = ((full_size - tiered_gb) / full_size * 100) if full_size > 0 else 0
    print(f"{'Tiered (recommended)':<30} {tiered_gb:>15.2f} GB   {tiered_savings:>10.1f}% saved")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print("\n✅ For your use case (Digital Twin with Learning):")
    print(f"\n   TIERED STORAGE is recommended:")
    print(f"     • Storage: {tiered_gb:.2f} GB for 3 years")
    print(f"     • Savings: {tiered_savings:.1f}% vs. storing all as FULL")
    print(f"     • Benefit: Full data available for recent emails (learning)")
    print(f"     • Benefit: Old unimportant emails automatically pruned")
    print(f"\n   All FULL is acceptable if:")
    print(f"     • Storage: {full_size:.2f} GB for 3 years")
    print(f"     • You value simplicity over storage optimization")
    print(f"     • You have adequate disk space (this is quite reasonable)")
    print(f"     • You want maximum data retention for compliance/learning")


def main():
    """Run all simulations"""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + " " * 20 + "EMAIL STORAGE SIMULATION" + " " * 34 + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    print_breakdown()
    print_simulation_table()
    print_tiered_simulation()
    print_comparison_summary()

    print("\n" + "=" * 80)
    print("Notes:")
    print("  • All sizes include 15% database overhead (indices, foreign keys)")
    print("  • Attachment sizes are averages; actual sizes vary widely")
    print("  • Compression not considered (SQLite doesn't compress by default)")
    print("  • Event log storage not included (typically <10% of email storage)")
    print("=" * 80)
    print()


if __name__ == '__main__':
    main()
