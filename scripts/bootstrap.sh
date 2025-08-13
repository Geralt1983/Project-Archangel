#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Bootstrapping Project Archangel development environment..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "📦 Virtual environment already exists"
fi

# Activate environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "📋 Installing Python dependencies..."
pip install -r requirements.txt

# Check for optional dependencies
echo "🔍 Checking optional dependencies..."

# Check tmux
if command -v tmux >/dev/null 2>&1; then
    echo "✅ tmux installed"
else
    echo "⚠️  tmux not found - install with: brew install tmux (macOS) or apt install tmux (Linux)"
fi

# Check Docker
if command -v docker >/dev/null 2>&1; then
    echo "✅ docker installed"
else
    echo "⚠️  docker not found - install from: https://docs.docker.com/get-docker/"
fi

# Check PostgreSQL
if command -v psql >/dev/null 2>&1; then
    echo "✅ postgresql client installed"
else
    echo "⚠️  postgresql client not found - install with: brew install postgresql (macOS)"
fi

echo ""
echo "🎉 Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Activate environment: source venv/bin/activate"
echo "  2. Start services: make up"
echo "  3. Initialize database: make init"
echo "  4. Run development environment: make dev"
echo ""
echo "Quick start: source venv/bin/activate && make dev"