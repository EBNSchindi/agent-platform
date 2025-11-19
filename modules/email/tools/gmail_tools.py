"""
Gmail Tools
@function_tool wrappers for Gmail API operations.
Based on patterns from 2_openai/ examples.
"""

import os
import base64
import pickle
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the token files
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]


class GmailService:
    """Gmail API service wrapper"""

    def __init__(self, account_id: str, credentials_path: str, token_path: str):
        """
        Initialize Gmail service for an account.

        Args:
            account_id: Account identifier (e.g., "gmail_1")
            credentials_path: Path to OAuth credentials JSON
            token_path: Path to save/load token
        """
        self.account_id = account_id
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate and build Gmail service"""
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        f"Please download OAuth credentials from Google Cloud Console"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        print(f"✅ Gmail service authenticated: {self.account_id}")

    def fetch_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails.

        Args:
            max_results: Maximum number of emails to fetch

        Returns:
            List of email dictionaries with id, subject, sender, snippet, body
        """
        try:
            # Query for unread messages
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])

            emails = []
            for msg in messages:
                # Get full message details
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                # Extract headers
                headers = message['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')

                # Get snippet and body
                snippet = message.get('snippet', '')
                body = self._get_email_body(message['payload'])

                emails.append({
                    'id': msg['id'],
                    'thread_id': message['threadId'],
                    'subject': subject,
                    'sender': sender,
                    'date': date_str,
                    'snippet': snippet,
                    'body': body,
                    'labels': message.get('labelIds', [])
                })

            return emails

        except HttpError as error:
            print(f'❌ Error fetching emails: {error}')
            return []

    def _get_email_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        else:
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        return body

    def create_draft(self, to: str, subject: str, body: str, in_reply_to: Optional[str] = None) -> Dict[str, str]:
        """
        Create a draft email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            in_reply_to: Optional message ID to reply to

        Returns:
            Dictionary with draft_id and status
        """
        try:
            # Create message
            message = MIMEText(body, 'html' if '<html>' in body.lower() else 'plain')
            message['to'] = to
            message['subject'] = subject

            if in_reply_to:
                message['In-Reply-To'] = in_reply_to
                message['References'] = in_reply_to

            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Create draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw}}
            ).execute()

            return {
                'status': 'success',
                'draft_id': draft['id'],
                'message': f'Draft created successfully'
            }

        except HttpError as error:
            return {
                'status': 'error',
                'error': str(error),
                'message': f'Failed to create draft: {error}'
            }

    def apply_label(self, email_id: str, label_name: str) -> Dict[str, str]:
        """
        Apply label to email.

        Args:
            email_id: Gmail message ID
            label_name: Label name to apply

        Returns:
            Dictionary with status
        """
        try:
            # Get or create label ID
            label_id = self._get_or_create_label(label_name)

            # Apply label
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'addLabelIds': [label_id]}
            ).execute()

            return {
                'status': 'success',
                'message': f'Label "{label_name}" applied to email {email_id}'
            }

        except HttpError as error:
            return {
                'status': 'error',
                'error': str(error),
                'message': f'Failed to apply label: {error}'
            }

    def _get_or_create_label(self, label_name: str) -> str:
        """Get label ID or create if doesn't exist"""
        try:
            # List existing labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
                    return label['id']

            # Create new label
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }

            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()

            return created_label['id']

        except HttpError as error:
            print(f'❌ Error with label: {error}')
            # Fallback to INBOX
            return 'INBOX'

    def archive_email(self, email_id: str) -> Dict[str, str]:
        """
        Archive email (remove from INBOX).

        Args:
            email_id: Gmail message ID

        Returns:
            Dictionary with status
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()

            return {
                'status': 'success',
                'message': f'Email {email_id} archived'
            }

        except HttpError as error:
            return {
                'status': 'error',
                'error': str(error),
                'message': f'Failed to archive email: {error}'
            }

    def mark_as_read(self, email_id: str) -> Dict[str, str]:
        """Mark email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            return {'status': 'success', 'message': f'Email {email_id} marked as read'}

        except HttpError as error:
            return {'status': 'error', 'message': str(error)}

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, str]:
        """
        Send email directly (for auto-reply mode).

        Args:
            to: Recipient
            subject: Subject line
            body: Email body

        Returns:
            Dictionary with status and message_id
        """
        try:
            message = MIMEText(body, 'html' if '<html>' in body.lower() else 'plain')
            message['to'] = to
            message['subject'] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            return {
                'status': 'success',
                'message_id': sent_message['id'],
                'message': f'Email sent to {to}'
            }

        except HttpError as error:
            return {
                'status': 'error',
                'error': str(error),
                'message': f'Failed to send email: {error}'
            }


# ============================================================================
# GLOBAL SERVICE CACHE
# ============================================================================

_gmail_services: Dict[str, GmailService] = {}


def get_gmail_service(account_id: str, credentials_path: str, token_path: str) -> GmailService:
    """
    Get or create Gmail service for account.
    Caches service instances to avoid re-authentication.
    """
    if account_id not in _gmail_services:
        _gmail_services[account_id] = GmailService(account_id, credentials_path, token_path)
    return _gmail_services[account_id]


# ============================================================================
# @function_tool WRAPPERS (for OpenAI Agents SDK)
# ============================================================================

# Note: These will be imported and used with @function_tool decorator
# when creating agents. For now, defined as regular functions.

def fetch_unread_emails_tool(account_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch unread emails from Gmail account.

    Args:
        account_id: Account identifier (gmail_1, gmail_2, gmail_3)
        max_results: Maximum number of emails to fetch

    Returns:
        List of email dictionaries
    """
    from agent_platform.core.config import Config

    account_config = Config.GMAIL_ACCOUNTS.get(account_id)
    if not account_config:
        return []

    service = get_gmail_service(
        account_id,
        account_config['credentials_path'],
        account_config['token_path']
    )

    return service.fetch_unread_emails(max_results)


def create_draft_tool(account_id: str, to: str, subject: str, body: str) -> Dict[str, str]:
    """
    Create draft email in Gmail account.

    Args:
        account_id: Account identifier
        to: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        Status dictionary with draft_id
    """
    from agent_platform.core.config import Config

    account_config = Config.GMAIL_ACCOUNTS.get(account_id)
    if not account_config:
        return {'status': 'error', 'message': f'Account {account_id} not found'}

    service = get_gmail_service(
        account_id,
        account_config['credentials_path'],
        account_config['token_path']
    )

    return service.create_draft(to, subject, body)


def apply_label_tool(account_id: str, email_id: str, label_name: str) -> Dict[str, str]:
    """Apply label to email"""
    from agent_platform.core.config import Config

    account_config = Config.GMAIL_ACCOUNTS.get(account_id)
    if not account_config:
        return {'status': 'error', 'message': f'Account {account_id} not found'}

    service = get_gmail_service(
        account_id,
        account_config['credentials_path'],
        account_config['token_path']
    )

    return service.apply_label(email_id, label_name)


def archive_email_tool(account_id: str, email_id: str) -> Dict[str, str]:
    """Archive email (remove from inbox)"""
    from agent_platform.core.config import Config

    account_config = Config.GMAIL_ACCOUNTS.get(account_id)
    if not account_config:
        return {'status': 'error', 'message': f'Account {account_id} not found'}

    service = get_gmail_service(
        account_id,
        account_config['credentials_path'],
        account_config['token_path']
    )

    return service.archive_email(email_id)
