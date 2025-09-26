#!/usr/bin/env python3
"""Quick authentication test"""

from huggingface_hub import login, whoami

# Your token
token = "YOUR_HF_TOKEN_HERE"  # Replace with your actual Hugging Face token

try:
    print("Testing authentication...")
    login(token=token, add_to_git_credential=False)

    info = whoami()
    print("SUCCESS: Authentication successful!")
    print(f"   User: {info['name']}")
    print(f"   Type: {info.get('type', 'unknown')}")

    # Save token for persistence
    from pathlib import Path

    token_dir = Path.home() / ".cache" / "huggingface"
    token_dir.mkdir(parents=True, exist_ok=True)

    with open(token_dir / "token", "w") as f:
        f.write(token)

    print("SUCCESS: Token saved for future sessions")

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
