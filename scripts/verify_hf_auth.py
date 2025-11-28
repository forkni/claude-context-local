#!/usr/bin/env python3
"""
HuggingFace Authentication Verification Script
Verifies HuggingFace authentication and EmbeddingGemma model access.
"""

import sys
from pathlib import Path


def check_huggingface_auth():
    """Check HuggingFace authentication status."""
    print("=== HuggingFace Authentication Verification ===\n")

    try:
        from huggingface_hub import whoami

        info = whoami()
        print(f"[OK] Authenticated as: {info['name']}")
        print(f"[INFO] Account type: {info.get('type', 'unknown')}")
        return True
    except Exception as e:
        print(f"[ERROR] Not authenticated: {e}")
        print("[HELP] You need to authenticate with HuggingFace")
        return False


def check_model_access():
    """Check access to the EmbeddingGemma model."""
    print("\n=== EmbeddingGemma Model Access ===\n")

    try:
        from huggingface_hub import model_info

        print("[INFO] Checking model info access...")
        info = model_info("google/embeddinggemma-300m")
        print(f"[OK] Model info accessible: {info.modelId}")
        print(f"[INFO] Model tags: {info.tags[:3] if info.tags else 'none'}")
        return True
    except Exception as e:
        print(f"[ERROR] Model access failed: {e}")
        print("[HELP] You may need to accept the model license")
        return False


def test_model_loading():
    """Test loading the EmbeddingGemma model."""
    print("\n=== Model Loading Test ===\n")

    try:
        from sentence_transformers import SentenceTransformer

        print("[INFO] Initializing SentenceTransformer...")
        print("[INFO] This may download the model (~1.3GB) if not cached...")

        model = SentenceTransformer("google/embeddinggemma-300m")
        print("[OK] Model loaded successfully!")

        # Test encoding
        print("[INFO] Testing model encoding...")
        test_text = "def test_function(): return True"
        embedding = model.encode(test_text)
        print(f"[OK] Encoding successful! Embedding dimension: {len(embedding)}")

        return True
    except Exception as e:
        print(f"[ERROR] Model loading failed: {e}")
        print("[HELP] This could indicate:")
        print("   1. Model license not accepted")
        print("   2. Authentication issues")
        print("   3. Network connectivity problems")
        return False


def print_help():
    """Print help information for authentication."""
    print("\n" + "=" * 60)
    print("AUTHENTICATION HELP")
    print("=" * 60)
    print("\nTo authenticate with HuggingFace:")
    print("1. Visit: https://huggingface.co/google/embeddinggemma-300m")
    print("2. Click 'Agree and access repository' if prompted")
    print("3. Get your token: https://huggingface.co/settings/tokens")
    print("4. Create a token with 'Read' permissions")
    print("\nAuthentication methods:")
    print("• Use the installer: install-windows.bat (includes auth step)")
    print(
        "• Manual authentication: scripts\\powershell\\hf_auth.ps1 -Token 'your_token'"
    )
    print("• Environment variable: set HF_TOKEN=hf_your_token_here")
    print("• CLI login: .venv\\Scripts\\uv.exe run huggingface-cli login")


def main():
    """Main verification function."""
    print("HuggingFace Authentication & Model Access Verification\n")

    # Check if we're in the right directory
    if not Path(".venv").exists():
        print("[ERROR] Virtual environment not found")
        print("[HELP] Run this script from the project root directory")
        print("[HELP] Make sure you've run install-windows.bat first")
        return False

    # Check Python environment
    venv_python = Path(".venv/Scripts/python.exe")
    if not venv_python.exists():
        print("[ERROR] Virtual environment Python not found")
        print("[HELP] Re-run install-windows.bat to fix the environment")
        return False

    print("[OK] Virtual environment found")

    # Run checks
    auth_ok = check_huggingface_auth()
    model_access_ok = check_model_access()

    if auth_ok and model_access_ok:
        model_loading_ok = test_model_loading()

        if model_loading_ok:
            print("\n" + "=" * 60)
            print("SUCCESS! All checks passed!")
            print("=" * 60)
            print("[OK] HuggingFace authentication: Working")
            print("[OK] Model access: Working")
            print("[OK] Model loading: Working")
            print("\nYou're ready to use the MCP server!")
            return True

    print("\n" + "=" * 60)
    print("VERIFICATION FAILED")
    print("=" * 60)

    if not auth_ok:
        print("[ERROR] HuggingFace authentication: Failed")
    if not model_access_ok:
        print("[ERROR] Model access: Failed")

    print_help()
    return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARN] Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Unexpected error: {e}")
        print("[HELP] Please report this issue with the full error message")
        sys.exit(1)
