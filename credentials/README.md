# Gmail API Credentials

Place your Gmail OAuth credentials JSON files here.

## Setup Instructions

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Gmail API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

4. Create OAuth Credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth Client ID"
   - Application type: **Desktop app**
   - Name: "Email Agent Platform - Account 1" (or similar)
   - Click "Create"

5. Download the JSON file:
   - Click the download button (⬇️) next to your credential
   - Save as `gmail_account_1.json` in this directory
   - Repeat for additional Gmail accounts (gmail_account_2.json, gmail_account_3.json)

6. Update `.env`:
   ```
   GMAIL_1_CREDENTIALS_PATH=credentials/gmail_account_1.json
   GMAIL_2_CREDENTIALS_PATH=credentials/gmail_account_2.json
   GMAIL_3_CREDENTIALS_PATH=credentials/gmail_account_3.json
   ```

## First Run

On first run, the script will:
1. Open a browser window
2. Ask you to sign in with your Gmail account
3. Request permissions to access Gmail
4. Save a token to `tokens/` directory for future use

## Files in this directory

- `gmail_account_1.json` - OAuth credentials for Gmail account 1
- `gmail_account_2.json` - OAuth credentials for Gmail account 2
- `gmail_account_3.json` - OAuth credentials for Gmail account 3
- `backup_credentials.json` - OAuth credentials for backup account

**⚠️ IMPORTANT: Never commit these files to Git! They are already in .gitignore**
