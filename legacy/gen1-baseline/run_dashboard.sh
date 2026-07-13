#!/bin/bash
# run_dashboard.sh: Launches the interactive M&E Copyright Infringement & Compliance Web UI
# Usage: ./run_dashboard.sh

cd "$(dirname "$0")"
export PYTHONPATH=.

streamlit run frontend/app.py --server.port 8501 --server.address localhost
