#!/bin/bash
# Start Options Scanner

cd /Users/cmondor/.openclaw/workspace/options-scanner
source .venv/bin/activate
streamlit run app.py --server.port 8502 --server.headless true --server.websocketPingInterval 20
