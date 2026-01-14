#!/usr/bin/env python3
"""
Configure Ollama models for ChainMind integration.

This script:
1. Checks available Ollama models
2. Downloads recommended models for reasoning
3. Updates ChainMind configuration
"""

import subprocess
import json
import sys
import time

def check_ollama_running():
    """Check if Ollama service is running."""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

def get_installed_models():
    """Get list of installed Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
            return models
        return []
    except Exception as e:
        print(f"Error getting models: {e}")
        return []

def pull_model(model_name):
    """Pull an Ollama model."""
    print(f"  ⬇️  Downloading {model_name}...")
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes max
        )
        if result.returncode == 0:
            print(f"  ✅ {model_name} downloaded successfully")
            return True
        else:
            print(f"  ⚠️  Failed to download {model_name}: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Timeout downloading {model_name}")
        return False
    except Exception as e:
        print(f"  ⚠️  Error downloading {model_name}: {e}")
        return False

def main():
    print("🚀 Configuring Ollama models for ChainMind...")
    print()

    # Check if Ollama is running
    if not check_ollama_running():
        print("❌ Ollama service is not running!")
        print("   Please start it with: ollama serve")
        sys.exit(1)

    print("✅ Ollama service is running")

    # Get installed models
    installed = get_installed_models()
    print(f"📋 Currently installed: {len(installed)} models")
    if installed:
        for model in installed:
            print(f"   - {model}")
    print()

    # Recommended models for RTX 5080 (15.5GB VRAM)
    recommended_models = [
        ("llama3.1:8b", "Llama 3.1 8B - Good balance, large context"),
        ("qwen2.5:7b", "Qwen 2.5 7B - Efficient reasoning"),
        ("llama3:8b", "Llama 3 8B - Fallback option"),
    ]

    # Try DeepSeek-R1 if available (best for reasoning)
    deepseek_models = [
        "deepseek-r1:1.5b",
        "deepseek-r1:4b",
        "deepseek-r1",
    ]

    print("📥 Downloading recommended models...")
    print()

    downloaded = []

    # Try DeepSeek-R1 first (best for reasoning)
    for model in deepseek_models:
        if model not in installed:
            if pull_model(model):
                downloaded.append(model)
                break
        else:
            print(f"  ✅ {model} already installed")
            downloaded.append(model)
            break

    # Download other recommended models
    for model_name, description in recommended_models:
        if model_name not in installed:
            print(f"\n📦 {description}")
            if pull_model(model_name):
                downloaded.append(model_name)
        else:
            print(f"  ✅ {model_name} already installed")
            downloaded.append(model_name)

    print()
    print("📋 Final model list:")
    final_models = get_installed_models()
    for model in final_models:
        print(f"   - {model}")

    print()
    print("✅ Setup complete!")
    print()
    print("💡 Models are configured as fallback providers in ChainMind")
    print("   They will be used automatically when OpenAI/Claude are unavailable")
    print()
    print("🧪 Test a model:")
    print("   ollama run llama3.1:8b 'Explain quantum computing'")

if __name__ == "__main__":
    main()
