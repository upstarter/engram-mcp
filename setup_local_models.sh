#!/bin/bash
# Setup Local Models for Reasoning
# =================================
# This script sets up Ollama with recommended models for reasoning tasks

set -e

echo "🚀 Setting up local models for reasoning..."

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Please install it first:"
    echo "   curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

echo "✅ Ollama is installed"

# Check if Ollama service is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama service is not running. Starting it..."
    # Try to start Ollama in background
    ollama serve > /tmp/ollama.log 2>&1 &
    OLLAMA_PID=$!
    echo "   Started Ollama (PID: $OLLAMA_PID)"
    echo "   Waiting for service to be ready..."
    sleep 5

    # Check if it's running now
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "❌ Failed to start Ollama. Please start it manually:"
        echo "   ollama serve"
        exit 1
    fi
fi

echo "✅ Ollama service is running"

# Get GPU info
GPU_VRAM=$(python3 -c "import torch; print(int(torch.cuda.get_device_properties(0).total_memory / (1024**3)))" 2>/dev/null || echo "0")
echo "📊 Detected GPU VRAM: ${GPU_VRAM}GB"

# Recommended models for RTX 5080 (15.5GB VRAM)
echo ""
echo "📥 Downloading recommended models for reasoning..."

# 1. DeepSeek-R1 (best for reasoning, ~8-12GB VRAM)
echo "  1. DeepSeek-R1 (best reasoning model)..."
if ollama list | grep -q "deepseek-r1"; then
    echo "     ✅ Already installed"
else
    echo "     ⬇️  Downloading deepseek-r1:1.5b (smaller, fits in 15.5GB)..."
    ollama pull deepseek-r1:1.5b || {
        echo "     ⚠️  deepseek-r1:1.5b not available, trying alternative..."
        ollama pull deepseek-r1:4b || echo "     ⚠️  DeepSeek-R1 not available in Ollama"
    }
fi

# 2. Llama 3.1 8B (good balance, ~6-8GB VRAM)
echo "  2. Llama 3.1 8B (good balance)..."
if ollama list | grep -q "llama3.1:8b"; then
    echo "     ✅ Already installed"
else
    echo "     ⬇️  Downloading llama3.1:8b..."
    ollama pull llama3.1:8b || echo "     ⚠️  Failed to download llama3.1:8b"
fi

# 3. Qwen3-4B-Reasoning (efficient reasoning, ~4-6GB VRAM)
echo "  3. Qwen3-4B-Reasoning (efficient reasoning)..."
if ollama list | grep -q "qwen3-4b-reasoning"; then
    echo "     ✅ Already installed"
else
    echo "     ⬇️  Downloading qwen3-4b-reasoning..."
    ollama pull richardyoung/qwen3-4b-reasoning || {
        echo "     ⚠️  qwen3-4b-reasoning not available, trying qwen2.5:7b..."
        ollama pull qwen2.5:7b || echo "     ⚠️  Qwen models not available"
    }
fi

# 4. Llama 3 8B (fallback option)
echo "  4. Llama 3 8B (fallback)..."
if ollama list | grep -q "llama3:8b"; then
    echo "     ✅ Already installed"
else
    echo "     ⬇️  Downloading llama3:8b..."
    ollama pull llama3:8b || echo "     ⚠️  Failed to download llama3:8b"
fi

echo ""
echo "📋 Installed models:"
ollama list

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Test a model: ollama run llama3.1:8b 'Explain quantum computing'"
echo "   2. Models are configured as fallback providers in ChainMind"
echo "   3. They will be used automatically when OpenAI/Claude are unavailable"
echo ""
echo "💡 Note: These models are fallback only. OpenAI/Claude are prioritized for quality."

