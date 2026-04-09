#!/bin/bash
# Pause sentinel, apply CSS fix, accept changes, resume
echo "=== Step 1: Pause Sentinel ==="
curl -s -X POST http://127.0.0.1:5000/api/sentinel/pause -H 'Content-Type: application/json'
echo ""

echo "=== Step 2: Apply CSS fix to WSL native ==="
python3 /mnt/c/Veritas_Lab/gravity-omega-v2/apply_shield_fix.py

echo ""
echo "=== Step 3: Accept changes (re-baseline in memory) ==="
curl -s -X POST http://127.0.0.1:5000/api/sentinel/accept -H 'Content-Type: application/json'
echo ""

echo "=== Step 4: Resume Sentinel ==="
curl -s -X POST http://127.0.0.1:5000/api/sentinel/resume -H 'Content-Type: application/json'
echo ""
echo "=== Done ==="
