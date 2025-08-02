#!/bin/bash

# Activate virtual environment
echo "🔁 Activating virtual environment..."
source .venv/bin/activate || { echo "❌ Error: .venv not found. Create one with 'python -m venv .venv'"; exit 1; }

# Export env vars
echo "🌍 Loading environment variables from .env..."
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "⚠️  Warning: .env file not found. Make sure OPENAI_API_KEY is set."
fi

# Install dependencies
echo "📦 Installing required packages..."
pip install -r requirements.txt

# Run the app
echo "🚀 Starting FastAPI app with Uvicorn..."
uvicorn app.api:app --host 0.0.0.0 --port 8001 --reload
if [ $? -ne 0 ]; then
  echo "❌ Error: Failed to start the FastAPI app."
  exit 1
fi