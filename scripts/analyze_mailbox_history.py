#!/usr/bin/env python3
"""
Mailbox History Analysis

Analyzes historical emails from a Gmail mailbox to:
1. Classify emails and initialize the system
2. Build sender/domain preferences for learning
3. Generate statistics on email distribution
4. Initialize vector database for RAG

Sampling strategy:
- Fetch 100-200 representative emails
- Mix of different time periods (recent and older)
- Different senders and categories

Usage:
    python scripts/analyze_mailbox_history.py

The script will:
1. Fetch emails from different time periods
2. Classify each email
3. Initialize sender/domain preferences
4. Generate comprehensive report
5. Optionally embed for vector database
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

from agent_platform.classification import UnifiedClassifier, EmailToClassify
from agent_platform.feedback import FeedbackTracker
from agent_platform.db.database import init_db, get_db
from agent_platform.db.models import ProcessedEmail, SenderPreference, DomainPreference


def load_environment():
    """Load environment variables."""
    load_dotenv()
    return {
        'openai_key': os.getenv('OPENAI_API_KEY'),
        'gmail_2_creds': os.getenv('GMAIL_2_CREDENTIALS_PATH'),
        'gmail_2_token': os.getenv('GMAIL_2_TOKEN_PATH'),
    }


def authenticate_gmail(creds_path: str, token_path: str) -> Any:
    """Authenticate with Gmail."""
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    creds = None

    if os.path.exists(token_path):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def fetch_sampled_emails(service, max_results: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch representative sample of emails from different time periods.

    Sampling strategy:
    - Recent emails (last 7 days): 40%
    - Week 2-4: 30%
    - Month 2-3: 20%
    - Older: 10%

    Args:
        service: Gmail service object
        max_results: Target number of emails

    Returns:
        List of email dictionaries
    """
    print(f"📊 Fetching representative email sample ({max_results} target)...")

    # Define time ranges for sampling
    now = datetime.utcnow()
    ranges = [
        ("recent", now - timedelta(days=7), now, 0.40),      # 40% last 7 days
        ("week2-4", now - timedelta(days=28), now - timedelta(days=7), 0.30),  # 30% week 2-4
        ("month2-3", now - timedelta(days=90), now - timedelta(days=28), 0.20),  # 20% month 2-3
        ("older", None, now - timedelta(days=90), 0.10),  # 10% older than 90 days
    ]

    all_emails = []
    total_fetched = 0

    for period_name, start_date, end_date, percentage in ranges:
        target_count = int(max_results * percentage)
        print(f"   Sampling {period_name}: {target_count} emails")

        # Build query
        if start_date:
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())
            query = f"after:{start_ts} before:{end_ts}"
        else:
            end_ts = int(end_date.timestamp())
            query = f"before:{end_ts}"

        try:
            # Get message IDs
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=target_count
            ).execute()

            messages = results.get('messages', [])
            print(f"      Found {len(messages)} emails")

            # Fetch details for each message
            for msg_id_obj in messages:
                msg_id = msg_id_obj['id']

                msg = service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='full'
                ).execute()

                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(no subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(unknown)')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')

                # Extract body
                body = ""
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            data = part['body'].get('data', '')
                            if data:
                                import base64
                                body = base64.urlsafe_b64decode(data).decode('utf-8')
                                break
                else:
                    data = msg['payload']['body'].get('data', '')
                    if data:
                        import base64
                        body = base64.urlsafe_b64decode(data).decode('utf-8')

                all_emails.append({
                    'id': msg_id,
                    'subject': subject,
                    'sender': sender,
                    'body': body,
                    'snippet': body[:500] if body else "(no body)",
                    'received_at': datetime.utcnow(),
                    'period': period_name,
                })

                total_fetched += 1

        except Exception as e:
            print(f"      ⚠️  Error fetching {period_name}: {e}")

    print(f"   Total fetched: {total_fetched} emails")
    return all_emails


async def classify_and_store(emails: List[Dict[str, Any]], db) -> Dict[str, Any]:
    """
    Classify emails and store in database with preferences.

    Args:
        emails: List of email dictionaries
        db: Database session

    Returns:
        Statistics dictionary
    """
    print(f"\n📊 Classifying {len(emails)} emails...")

    classifier = UnifiedClassifier()
    feedback_tracker = FeedbackTracker(db=db)

    stats = {
        'total_classified': 0,
        'by_category': defaultdict(int),
        'by_confidence': {'high': 0, 'medium': 0, 'low': 0},
        'by_layer': defaultdict(int),
        'sender_preferences_initialized': 0,
        'avg_processing_time': 0,
        'processing_times': [],
    }

    # Classify each email
    for i, email in enumerate(emails, 1):
        if i % 50 == 0:
            print(f"   Progress: {i}/{len(emails)}")

        # Create EmailToClassify
        email_to_classify = EmailToClassify(
            email_id=email['id'],
            account_id='gmail_2',
            sender=email['sender'],
            subject=email['subject'],
            body=email['body'],
            received_at=email['received_at'],
        )

        try:
            # Classify
            classification = await classifier.classify(email_to_classify)

            # Store in database
            processed_email = ProcessedEmail(
                account_id=1,  # Gmail account 2
                email_id=email['id'],
                sender=email['sender'],
                subject=email['subject'],
                received_at=email['received_at'],
                processed_at=datetime.utcnow(),
                category=classification.category,
                importance_score=classification.importance,
                classification_confidence=classification.confidence,
                llm_provider_used=classification.llm_provider_used or f"{classification.layer_used}_only",
                extra_metadata={
                    'layer_used': classification.layer_used,
                    'processing_time_ms': classification.processing_time_ms,
                    'period': email.get('period', 'unknown'),
                }
            )

            db.add(processed_email)
            stats['total_classified'] += 1
            stats['by_category'][classification.category] += 1

            # Track confidence level
            if classification.confidence >= 0.85:
                stats['by_confidence']['high'] += 1
            elif classification.confidence >= 0.60:
                stats['by_confidence']['medium'] += 1
            else:
                stats['by_confidence']['low'] += 1

            stats['by_layer'][classification.layer_used] += 1
            stats['processing_times'].append(classification.processing_time_ms)

            # Track as "positive" feedback for initial preference building
            # This helps initialize sender/domain preferences
            if classification.category in ['wichtig', 'action_required']:
                feedback_tracker.track_reply(
                    email_id=email['id'],
                    sender_email=email['sender'],
                    account_id='gmail_2'
                )
                stats['sender_preferences_initialized'] += 1

        except Exception as e:
            print(f"      ⚠️  Error classifying email {email['id']}: {e}")

    # Commit all changes
    db.commit()

    # Calculate statistics
    if stats['processing_times']:
        stats['avg_processing_time'] = sum(stats['processing_times']) / len(stats['processing_times'])

    print(f"   ✅ Classification complete")
    return stats


async def run_mailbox_analysis():
    """Run the complete mailbox analysis."""
    print("=" * 70)
    print("MAILBOX HISTORY ANALYSIS")
    print("=" * 70)
    print()

    # Load environment
    env = load_environment()

    # Validate
    if not os.path.exists(env['gmail_2_creds']):
        print(f"❌ Gmail credentials not found: {env['gmail_2_creds']}")
        return False

    # Initialize database
    print("🗄️  Initializing database...")
    init_db()
    print("   ✅ Database ready")
    print()

    # Authenticate
    print("🔐 Authenticating with Gmail...")
    try:
        service = authenticate_gmail(env['gmail_2_creds'], env['gmail_2_token'])
        print("   ✅ Gmail authentication successful")
    except Exception as e:
        print(f"   ❌ Gmail authentication failed: {e}")
        return False
    print()

    # Fetch emails
    emails = fetch_sampled_emails(service, max_results=200)

    if not emails:
        print("   ℹ️  No emails found in mailbox")
        return True

    print()

    # Classify and store
    with get_db() as db:
        stats = await classify_and_store(emails, db)

    # Print report
    print()
    print("=" * 70)
    print("ANALYSIS REPORT")
    print("=" * 70)
    print()
    print(f"Total Classified: {stats['total_classified']}")
    print(f"Average Processing Time: {stats['avg_processing_time']:.0f}ms")
    print()

    print("By Category:")
    for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
        pct = count / stats['total_classified'] * 100 if stats['total_classified'] > 0 else 0
        print(f"   {category:20s}: {count:3d} ({pct:5.1f}%)")
    print()

    print("By Confidence Level:")
    print(f"   High (≥0.85):     {stats['by_confidence']['high']:3d} ({stats['by_confidence']['high']/stats['total_classified']*100:5.1f}%)" if stats['total_classified'] > 0 else "   High (≥0.85):     0")
    print(f"   Medium (0.6-0.85): {stats['by_confidence']['medium']:3d} ({stats['by_confidence']['medium']/stats['total_classified']*100:5.1f}%)" if stats['total_classified'] > 0 else "   Medium (0.6-0.85): 0")
    print(f"   Low (<0.6):       {stats['by_confidence']['low']:3d} ({stats['by_confidence']['low']/stats['total_classified']*100:5.1f}%)" if stats['total_classified'] > 0 else "   Low (<0.6):       0")
    print()

    print("By Classification Layer:")
    for layer, count in sorted(stats['by_layer'].items(), key=lambda x: x[1], reverse=True):
        pct = count / stats['total_classified'] * 100 if stats['total_classified'] > 0 else 0
        print(f"   {layer:20s}: {count:3d} ({pct:5.1f}%)")
    print()

    print(f"Sender Preferences Initialized: {stats['sender_preferences_initialized']}")
    print()

    print("=" * 70)
    print("✅ MAILBOX ANALYSIS COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review database records: python scripts/view_classification_results.py")
    print("2. View sender preferences: python scripts/view_sender_preferences.py")
    print("3. Set up vector database for RAG: python scripts/setup_vector_db.py")
    print()

    return True


def main():
    """Main entry point."""
    try:
        success = asyncio.run(run_mailbox_analysis())
        sys.exit(0 if success else 1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ANALYSIS FAILED: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
