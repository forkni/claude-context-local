#!/usr/bin/env python3
"""Quick authentication test"""

import sys
from huggingface_hub import login, whoami, HfFolder

# Get existing token or skip test
token = HfFolder.get_token()

if not token:
    print("SKIP: No HuggingFace token available")
    print("To authenticate, run: huggingface-cli login")
    sys.exit(0)

try:
    print("Testing authentication...")
    # Token is already stored, just verify it works
    # login(token=token, add_to_git_credential=False)  # Not needed if token already exists

    info = whoami()
    print("SUCCESS: Authentication successful!")
    print(f"   User: {info['name']}")
    print(f"   Type: {info.get('type', 'unknown')}")
    print(f"   Token: {'claude-context-local' if 'claude-context-local' in str(info) else 'Valid'}")

    print("SUCCESS: Authentication verified!")

except Exception as e:
    print(f"ERROR: Authentication failed: {e}")
    exit(1)

# Test model access
try:
    print("\nTesting model access...")
    from huggingface_hub import model_info

    info = model_info("google/embeddinggemma-300m")
    print(f"SUCCESS: Model access confirmed: {info.modelId}")

except Exception as e:
    print(f"ERROR: Model access failed: {e}")
    print("Visit https://huggingface.co/google/embeddinggemma-300m to accept terms")
    exit(1)

print("\nSUCCESS: All tests passed! Ready for MCP server.")
