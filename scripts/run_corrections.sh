#!/bin/bash
# Script manuel — Lance les 2 agents de correction
# Usage: ./run_corrections.sh

set -e

echo "=================================="
echo "🤖 PIPELINE CORRECTIONS COMMUNES"
echo "=================================="

cd /volume1/docker/color-communes

# 1. Correction communes UNKNOWN
echo ""
echo "1️⃣ Correction communes UNKNOWN..."
python3 auto_correct_communes.py
CORRECTED=$?

echo ""

# 2. Enrichissement GeoJSON
echo "2️⃣ Enrichissement GeoJSON..."
python3 auto_enrich_geojson.py
GEOJSON=$?

echo ""
echo "=================================="
echo "✅ PIPELINE TERMINÉ"
echo "=================================="

if [ $CORRECTED -eq 0 ]; then
    echo "✓ Corrections: OK"
else
    echo "✗ Corrections: ERREUR"
fi

if [ $GEOJSON -eq 0 ]; then
    echo "✓ GeoJSON: OK"
else
    echo "✗ GeoJSON: ERREUR"
fi

echo ""
echo "📌 Prochaine étape:"
echo "   sudo /usr/local/bin/docker-compose restart"
echo ""
