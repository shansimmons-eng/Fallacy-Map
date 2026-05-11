#!/bin/bash
# GPG Signature Setup for KylosArc Inverion Engine
# Run this script to configure commit signing

echo "=== KylosArc GPG Signature Setup ==="
echo ""

# Check for GPG
if ! command -v gpg &> /dev/null; then
    echo "ERROR: GPG not found. Please install GnuPG."
    exit 1
fi

# Enable commit signing
git config --global commit.gpgsign true
echo "[OK] Commit signing enabled"

# Detect GPG executable
GPG_PATH=$(which gpg 2>/dev/null || which gpg2 2>/dev/null || echo "gpg")
git config --global gpg.program "$GPG_PATH"
echo "[OK] GPG program: $GPG_PATH"

# Check for existing keys
echo ""
echo "Checking for existing GPG keys..."
KEY_INFO=$(gpg --list-secret-keys 2>/dev/null | grep -E "sec|sub" | head -5)

if [ -z "$KEY_INFO" ]; then
    echo ""
    echo "NO GPG KEYS FOUND."
    echo ""
    echo "To create a signing key, run:"
    echo "  gpg --full-generate-key"
    echo ""
    echo "Or use GitHub's instructions:"
    echo "  https://docs.github.com/en/github/authenticating-to-github/generating-a-new-gpg-key"
    echo ""
    echo "Once you have a key, it will be automatically used for commits."
    echo ""
    echo "VERIFICATION STATUS: PENDING"
else
    echo "Found existing keys:"
    echo "$KEY_INFO"
    echo ""
    echo "VERIFICATION STATUS: READY"
fi

# List SSH keys as alternative
echo ""
echo "Alternative: SSH signing"
if [ -f ~/.ssh/id_ed25519.pub ]; then
    echo "[OK] Ed25519 SSH key found at ~/.ssh/id_ed25519.pub"
elif [ -f ~/.ssh/id_rsa.pub ]; then
    echo "[OK] RSA SSH key found at ~/.ssh/id_rsa.pub"
else
    echo "[INFO] No SSH keys found. SSH signing is optional."
fi

echo ""
echo "=== Configuration Complete ==="
echo ""
echo "Current git signing config:"
git config --global --list | grep -E "sign|gpgsign|gpg" || echo "(none set)"