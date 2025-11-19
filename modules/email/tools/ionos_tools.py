"""
Ionos Mail Tools
IMAP/SMTP tools for Ionos email account.
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from datetime import datetime

from agent_platform.core.config import Config


class IonosService:
    """Ionos IMAP/SMTP service wrapper"""

    def __init__(self):
        """Initialize with config from environment"""
        self.email = Config.IONOS_ACCOUNT['email']
        self.password = Config.IONOS_ACCOUNT['password']
        self.imap_server = Config.IONOS_ACCOUNT['imap_server']
        self.imap_port = Config.IONOS_ACCOUNT['imap_port']
        self.smtp_server = Config.IONOS_ACCOUNT['smtp_server']
        self.smtp_port = Config.IONOS_ACCOUNT['smtp_port']

    def fetch_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails via IMAP.

        Returns:
            List of email dictionaries
        """
        try:
            # Connect to IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email, self.password)
            mail.select('INBOX')

            # Search for unread emails
            status, messages = mail.search(None, 'UNSEEN')

            if status != 'OK':
                return []

            email_ids = messages[0].split()
            emails = []

            # Fetch latest max_results emails
            for email_id in email_ids[-max_results:]:
                status, msg_data = mail.fetch(email_id, '(RFC822)')

                if status != 'OK':
                    continue

                # Parse email
                msg = email.message_from_bytes(msg_data[0][1])

                # Extract headers
                subject = msg.get('Subject', 'No Subject')
                sender = msg.get('From', 'Unknown')
                date_str = msg.get('Date', '')

                # Get body
                body = self._get_email_body(msg)

                emails.append({
                    'id': email_id.decode(),
                    'subject': subject,
                    'sender': sender,
                    'date': date_str,
                    'body': body,
                    'snippet': body[:200] if body else ''
                })

            mail.close()
            mail.logout()

            return emails

        except Exception as e:
            print(f'❌ Error fetching Ionos emails: {e}')
            return []

    def _get_email_body(self, msg) -> str:
        """Extract email body from message"""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
                elif content_type == 'text/html' and not body:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(msg.get_payload())

        return body

    def create_draft(self, to: str, subject: str, body: str) -> Dict[str, str]:
        """
        Create draft email.
        Note: IMAP doesn't directly support drafts like Gmail API,
        so we save to Drafts folder.

        Args:
            to: Recipient
            subject: Subject
            body: Email body

        Returns:
            Status dictionary
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html' if '<html>' in body.lower() else 'plain'))

            # Connect to IMAP and save to Drafts
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email, self.password)

            # Append to Drafts folder
            mail.append('Drafts', '', imaplib.Time2Internaldate(datetime.now()), msg.as_bytes())

            mail.logout()

            return {
                'status': 'success',
                'message': f'Draft saved to Ionos Drafts folder'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to create draft: {e}'
            }

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, str]:
        """
        Send email via SMTP.

        Args:
            to: Recipient
            subject: Subject
            body: Email body

        Returns:
            Status dictionary
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html' if '<html>' in body.lower() else 'plain'))

            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)

            return {
                'status': 'success',
                'message': f'Email sent to {to}'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to send email: {e}'
            }

    def apply_label(self, email_id: str, folder: str) -> Dict[str, str]:
        """
        Move/copy email to folder (IMAP equivalent of label).

        Args:
            email_id: Email UID
            folder: Folder name

        Returns:
            Status dictionary
        """
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email, self.password)
            mail.select('INBOX')

            # Copy to folder
            mail.copy(email_id, folder)

            mail.logout()

            return {
                'status': 'success',
                'message': f'Email copied to folder: {folder}'
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to move email: {e}'
            }

    def archive_email(self, email_id: str) -> Dict[str, str]:
        """
        Archive email (move to Archive folder).

        Args:
            email_id: Email UID

        Returns:
            Status dictionary
        """
        return self.apply_label(email_id, 'Archive')


# ============================================================================
# GLOBAL SERVICE INSTANCE
# ============================================================================

_ionos_service = None


def get_ionos_service() -> IonosService:
    """Get or create Ionos service instance"""
    global _ionos_service
    if _ionos_service is None:
        _ionos_service = IonosService()
    return _ionos_service


# ============================================================================
# TOOL FUNCTIONS
# ============================================================================

def fetch_ionos_emails(max_results: int = 10) -> List[Dict[str, Any]]:
    """Fetch unread emails from Ionos account"""
    service = get_ionos_service()
    return service.fetch_unread_emails(max_results)


def create_ionos_draft(to: str, subject: str, body: str) -> Dict[str, str]:
    """Create draft in Ionos account"""
    service = get_ionos_service()
    return service.create_draft(to, subject, body)


def send_ionos_email(to: str, subject: str, body: str) -> Dict[str, str]:
    """Send email via Ionos SMTP"""
    service = get_ionos_service()
    return service.send_email(to, subject, body)


def archive_ionos_email(email_id: str) -> Dict[str, str]:
    """Archive Ionos email"""
    service = get_ionos_service()
    return service.archive_email(email_id)
