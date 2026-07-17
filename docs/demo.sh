#!/usr/bin/env bash
# Demo script for Latchkey asciinema recording
# Simulates: left = cron failing, right = latchkey succeeding

set -e

# Simulate a cron job hitting a Keychain prompt (failure path)
echo "$ echo \"Getting GitHub token...\""
sleep 0.5
echo "Getting GitHub token..."
sleep 0.8
echo "Security:钟 wants to use your confidential information stored in \"github\" in your keychain."
sleep 0.6
echo "To allow this, enter the \"login\" keychain password: "
sleep 0.8
echo ""
echo "[Cron job timed out waiting for interactive auth]"
echo "✗ Failed to get credential after 30s timeout"
sleep 0.5
echo ""
echo ""

# Now show the same job with Latchkey
echo "$ pip install latchkey"
sleep 0.4
echo "Successfully installed latchkey-0.1.0 cryptography-43.0.3"
sleep 0.6

echo "$ latchkey bootstrap"
sleep 0.3
echo "✓ Store initialized (~/.latchkey/.master_key)"
sleep 0.5
echo ""
echo "  Importing: ~/Downloads/Google Passwords.csv"
sleep 0.4
echo "  Imported: 17 credentials"
echo "  Skipped:  3 (duplicates)"
sleep 0.3
echo ""
echo "  Spot-check:"
echo "  ✓ github.com (https://github.com)"
echo "  ✓ pypi.org (https://pypi.org)"
echo "  ✓ dev.to (https://dev.to)"
sleep 0.5
echo ""
echo "✓ Bootstrap complete. 17 credentials ready."
sleep 0.3

echo "$ latchkey serve &"
sleep 0.3
echo "[1] 84321"
echo "Latchkey listening on ~/.latchkey/latchkey.sock"
sleep 0.5

echo "$ python3 -c \"from latchkey.client import get_credential; print(get_credential('github.com')['password'])\""
sleep 0.4
echo "ghp_y0u_w0uld_n3v3r_gu3ss_this_token"
sleep 0.6
echo ""
echo "✓ Cron job completed — no keychain prompt, no failed retries."
sleep 0.3
