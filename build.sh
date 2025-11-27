#!/bin/bash
echo "🔧 Starting build process on Render..."

# Set Python path
export PYTHONPATH=/opt/render/project/src

# Upgrade pip and setuptools
python -m pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements.txt

echo "✅ Build completed successfully!"
