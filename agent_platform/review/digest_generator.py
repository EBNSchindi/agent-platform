"""
Daily Digest Generator

Generates HTML email summaries of pending review items for user review.
Creates formatted, actionable digest emails with classification suggestions
and easy approval/rejection options.

This is used by the scheduler to send daily digest emails to users.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from agent_platform.db.models import ReviewQueueItem
from agent_platform.db.database import get_db
from agent_platform.review.queue_manager import ReviewQueueManager


class DailyDigestGenerator:
    """
    Generates daily digest emails for review queue items.

    Creates formatted HTML emails with:
    - Summary statistics
    - List of emails requiring review
    - Classification suggestions with reasoning
    - Action buttons/links for approval/rejection
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize digest generator.

        Args:
            db: Optional database session
        """
        self.db = db
        self._owns_db = False

        if not self.db:
            self.db = get_db().__enter__()
            self._owns_db = True

        self.queue_manager = ReviewQueueManager(db=self.db)

    def __del__(self):
        """Clean up database session if we created it."""
        if self._owns_db and self.db:
            try:
                self.db.close()
            except:
                pass

    # ========================================================================
    # MAIN GENERATION METHODS
    # ========================================================================

    def generate_digest(
        self,
        account_id: Optional[str] = None,
        hours_back: int = 24,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a daily digest for review queue items.

        Args:
            account_id: Optional account ID to filter by
            hours_back: Only include items from last N hours (default: 24)
            limit: Maximum number of items to include

        Returns:
            Dictionary with:
            - items: List of ReviewQueueItems
            - html: HTML content for email
            - text: Plain text content for email
            - summary: Summary statistics
        """
        # Get items for digest
        items = self.queue_manager.get_items_for_digest(
            account_id=account_id,
            hours_back=hours_back,
            limit=limit,
        )

        if not items:
            return {
                "items": [],
                "html": self._generate_empty_digest_html(account_id),
                "text": self._generate_empty_digest_text(account_id),
                "summary": {
                    "total_items": 0,
                    "by_category": {},
                    "accounts": [],
                },
            }

        # Generate summary statistics
        summary = self._generate_summary_stats(items)

        # Generate HTML and text content
        html_content = self._generate_html_digest(items, summary, account_id)
        text_content = self._generate_text_digest(items, summary, account_id)

        return {
            "items": items,
            "html": html_content,
            "text": text_content,
            "summary": summary,
        }

    # ========================================================================
    # HTML GENERATION
    # ========================================================================

    def _generate_html_digest(
        self,
        items: List[ReviewQueueItem],
        summary: Dict[str, Any],
        account_id: Optional[str],
    ) -> str:
        """Generate HTML content for digest email."""
        # Header
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            margin-top: 0;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary {{
            background-color: #ecf0f1;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .summary h2 {{
            margin-top: 0;
            color: #2c3e50;
            font-size: 18px;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        .stat {{
            background-color: white;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            font-size: 12px;
            color: #7f8c8d;
            text-transform: uppercase;
        }}
        .email-item {{
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 20px;
            margin: 20px 0;
            transition: box-shadow 0.3s;
        }}
        .email-item:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .email-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }}
        .email-subject {{
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
            margin: 0 0 5px 0;
        }}
        .email-sender {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        .email-snippet {{
            color: #555;
            font-size: 14px;
            margin: 10px 0;
            padding: 10px;
            background-color: #f9f9f9;
            border-left: 3px solid #ecf0f1;
            border-radius: 4px;
        }}
        .classification {{
            margin: 15px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }}
        .classification-header {{
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 8px;
        }}
        .category-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            margin-right: 10px;
        }}
        .category-wichtig {{ background-color: #e74c3c; color: white; }}
        .category-action_required {{ background-color: #e67e22; color: white; }}
        .category-nice_to_know {{ background-color: #3498db; color: white; }}
        .category-newsletter {{ background-color: #9b59b6; color: white; }}
        .category-spam {{ background-color: #95a5a6; color: white; }}
        .category-system_notifications {{ background-color: #1abc9c; color: white; }}
        .confidence-bar {{
            width: 100%;
            height: 8px;
            background-color: #ecf0f1;
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }}
        .confidence-fill {{
            height: 100%;
            background: linear-gradient(to right, #e74c3c, #f39c12, #27ae60);
            transition: width 0.3s;
        }}
        .reasoning {{
            color: #555;
            font-size: 13px;
            font-style: italic;
            margin: 8px 0;
        }}
        .actions {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }}
        .btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }}
        .btn-approve {{
            background-color: #27ae60;
            color: white;
        }}
        .btn-approve:hover {{
            background-color: #229954;
        }}
        .btn-reject {{
            background-color: #e74c3c;
            color: white;
        }}
        .btn-reject:hover {{
            background-color: #c0392b;
        }}
        .btn-modify {{
            background-color: #3498db;
            color: white;
        }}
        .btn-modify:hover {{
            background-color: #2980b9;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
        }}
        .importance-value {{
            display: inline-block;
            padding: 2px 8px;
            background-color: #ecf0f1;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            color: #555;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Email Review Digest</h1>

        <div class="summary">
            <h2>Summary</h2>
            <div class="summary-stats">
                <div class="stat">
                    <div class="stat-value">{summary['total_items']}</div>
                    <div class="stat-label">Items to Review</div>
                </div>
"""

        # Add category breakdown
        for category, count in summary['by_category'].items():
            html += f"""
                <div class="stat">
                    <div class="stat-value">{count}</div>
                    <div class="stat-label">{category.replace('_', ' ').title()}</div>
                </div>
"""

        html += """
            </div>
        </div>
"""

        # Add individual email items
        for item in items:
            confidence_pct = int(item.confidence * 100)
            importance_pct = int(item.importance_score * 100)

            html += f"""
        <div class="email-item">
            <div class="email-header">
                <div>
                    <h3 class="email-subject">{self._escape_html(item.subject or 'No Subject')}</h3>
                    <div class="email-sender">From: {self._escape_html(item.sender or 'Unknown')}</div>
                </div>
            </div>

            {f'<div class="email-snippet">{self._escape_html(item.snippet[:200] + "..." if item.snippet and len(item.snippet) > 200 else item.snippet or "")}</div>' if item.snippet else ''}

            <div class="classification">
                <div class="classification-header">Suggested Classification</div>
                <div>
                    <span class="category-badge category-{item.suggested_category}">{item.suggested_category.replace('_', ' ').title()}</span>
                    <span class="importance-value">Importance: {importance_pct}%</span>
                </div>
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">
                    Confidence: {confidence_pct}%
                </div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: {confidence_pct}%;"></div>
                </div>
                {f'<div class="reasoning">{self._escape_html(item.reasoning)}</div>' if item.reasoning else ''}
            </div>

            <div class="actions">
                <a href="mailto:review@system.local?subject=Approve%20{item.id}" class="btn btn-approve">✓ Approve</a>
                <a href="mailto:review@system.local?subject=Reject%20{item.id}" class="btn btn-reject">✗ Reject</a>
                <a href="mailto:review@system.local?subject=Modify%20{item.id}" class="btn btn-modify">✎ Modify</a>
            </div>
        </div>
"""

        # Footer
        html += f"""
        <div class="footer">
            <p>Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
            <p>This digest contains emails from the last {24} hours that require your review.</p>
            {f'<p>Account: {account_id}</p>' if account_id else ''}
        </div>
    </div>
</body>
</html>
"""

        return html

    def _generate_empty_digest_html(self, account_id: Optional[str]) -> str:
        """Generate HTML for empty digest (no items to review)."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #27ae60;
            margin: 0;
        }}
        .icon {{
            font-size: 64px;
            margin: 20px 0;
        }}
        p {{
            color: #7f8c8d;
            font-size: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">✓</div>
        <h1>All Caught Up!</h1>
        <p>No emails require review at this time.</p>
        {f'<p style="font-size: 14px;">Account: {account_id}</p>' if account_id else ''}
        <p style="font-size: 12px; margin-top: 30px;">Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
</body>
</html>
"""

    # ========================================================================
    # TEXT GENERATION
    # ========================================================================

    def _generate_text_digest(
        self,
        items: List[ReviewQueueItem],
        summary: Dict[str, Any],
        account_id: Optional[str],
    ) -> str:
        """Generate plain text content for digest email."""
        text = f"""
EMAIL REVIEW DIGEST
{'=' * 70}

SUMMARY
{'-' * 70}
Total Items to Review: {summary['total_items']}

Breakdown by Category:
"""

        for category, count in summary['by_category'].items():
            text += f"  {category.replace('_', ' ').title()}: {count}\n"

        text += f"\n{'=' * 70}\n\n"

        # Add individual items
        for i, item in enumerate(items, 1):
            confidence_pct = int(item.confidence * 100)
            importance_pct = int(item.importance_score * 100)

            text += f"""
ITEM {i}/{len(items)}
{'-' * 70}
Subject: {item.subject or 'No Subject'}
From: {item.sender or 'Unknown'}
"""

            if item.snippet:
                snippet = item.snippet[:150] + "..." if len(item.snippet) > 150 else item.snippet
                text += f"Preview: {snippet}\n"

            text += f"""
Suggested Category: {item.suggested_category.replace('_', ' ').upper()}
Importance: {importance_pct}%
Confidence: {confidence_pct}%
"""

            if item.reasoning:
                text += f"Reasoning: {item.reasoning}\n"

            text += f"""
Actions:
  [Approve] mailto:review@system.local?subject=Approve%20{item.id}
  [Reject]  mailto:review@system.local?subject=Reject%20{item.id}
  [Modify]  mailto:review@system.local?subject=Modify%20{item.id}

{'=' * 70}
"""

        # Footer
        text += f"""

Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
This digest contains emails from the last 24 hours that require your review.
"""

        if account_id:
            text += f"Account: {account_id}\n"

        return text

    def _generate_empty_digest_text(self, account_id: Optional[str]) -> str:
        """Generate plain text for empty digest."""
        text = f"""
EMAIL REVIEW DIGEST
{'=' * 70}

All Caught Up!

No emails require review at this time.
"""

        if account_id:
            text += f"\nAccount: {account_id}\n"

        text += f"\nGenerated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"

        return text

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_summary_stats(
        self,
        items: List[ReviewQueueItem],
    ) -> Dict[str, Any]:
        """Generate summary statistics from items."""
        by_category = {}
        accounts = set()

        for item in items:
            # Count by category
            by_category[item.suggested_category] = by_category.get(
                item.suggested_category, 0
            ) + 1

            # Track accounts
            accounts.add(item.account_id)

        return {
            "total_items": len(items),
            "by_category": by_category,
            "accounts": list(accounts),
        }

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""

        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text
