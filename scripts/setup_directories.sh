#!/bin/bash
# Setup script to create necessary directories for Email Classification System

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "========================================================================"
echo "Email Classification System - Directory Setup"
echo "========================================================================"
echo ""

# Create directories
echo "📁 Creating necessary directories..."

mkdir -p credentials
echo "   ✅ credentials/"

mkdir -p tokens
echo "   ✅ tokens/"

mkdir -p logs
echo "   ✅ logs/"

mkdir -p data
echo "   ✅ data/"

mkdir -p exports
echo "   ✅ exports/"

# Create .gitignore files to protect sensitive data
echo ""
echo "🔒 Protecting sensitive files with .gitignore..."

# credentials/.gitignore
cat > credentials/.gitignore << 'EOF'
# Protect all credential files
*.json
*.pem
*.key
!.gitignore
EOF
echo "   ✅ credentials/.gitignore"

# tokens/.gitignore
cat > tokens/.gitignore << 'EOF'
# Protect all token files
*.json
*.token
!.gitignore
EOF
echo "   ✅ tokens/.gitignore"

# logs/.gitignore
cat > logs/.gitignore << 'EOF'
# Protect log files
*.log
*.txt
!.gitignore
EOF
echo "   ✅ logs/.gitignore"

echo ""
echo "========================================================================"
echo "✅ Directory setup complete!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "1. Download Gmail OAuth2 credentials:"
echo "   - Go to https://console.cloud.google.com/"
echo "   - Create OAuth2 credentials (Desktop app)"
echo "   - Download as JSON"
echo "   - Save to: credentials/gmail_account_2.json"
echo ""
echo "2. Configure .env:"
echo "   - Update OPENAI_API_KEY"
echo "   - Update GMAIL_2_EMAIL"
echo "   - Update GMAIL_2_CREDENTIALS_PATH if needed"
echo ""
echo "3. Run Gmail authentication test:"
echo "   python scripts/test_gmail_auth.py"
echo ""
echo "4. Run E2E tests:"
echo "   python tests/test_e2e_real_gmail.py"
echo ""
