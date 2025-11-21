#!/usr/bin/env python3
"""
Get OAuth URL for gmail_3 account
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

creds_path = os.getenv('GMAIL_3_CREDENTIALS_PATH')

flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
flow.redirect_uri = 'http://localhost:8080/'
auth_url, _ = flow.authorization_url(prompt='consent')

print("\n" + "="*70)
print("GMAIL_3 OAUTH URL")
print("="*70)
print()
print(auth_url)
print()
print("="*70)
print("Account: ebn.veranstaltungen.consulting@gmail.com")
print("="*70)
