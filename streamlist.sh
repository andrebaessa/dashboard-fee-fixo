#!/bin/bash
source ~/dashboard_fee_fixo/venv/bin/activate
cd ~/dashboard_fee_fixo
streamlit run app.py --server.port=8080 --server.enableCORS=false

