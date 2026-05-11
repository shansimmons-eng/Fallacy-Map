#!/bin/bash
# Setup script for Fallacy Map

set -e

cd "$(dirname "$0")"

echo "Creating Python virtual environment..."
python3 -m venv venv

echo "Activating venv and installing requirements..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "To run the backend:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "To run the frontend:"
echo "  cd fallacy_map/frontend"
echo "  npm install"
echo "  npm run dev"