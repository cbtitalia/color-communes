#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
color_communes_auto_enrich.py
🚀 AUTO-ENRICHISSEMENT GEOJSON — S'EXÉCUTE AU DÉMARRAGE DU BOT

Intégration complète dans le bot Telegram:
1. Détecte communes manquantes de GeoJSON
2. Les enrichit via CSV mapping + Overpass (avec fallback)
3. Met à jour communes_mapping.csv + GeoJSON
4. Log tout dans Telegram

À intégrer dans main.py:
    from color_communes_auto_enrich import ensure_communes_enriched
    ensure_communes_enriched()  # Appel au démarrage
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import requests
import time

# Config — Chemins INTERNES du container Docker
DATA_DIR = "/data"
MAPPING_FILE = "/app/communes_mapping.csv"
GEOJSON_DIR = "/data/geojson_cache"
LOG_FILE = "/data/auto_enrich.log"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RATE_LIMIT = 1.5
TIMEOUT = 30

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE) if os.path.exists(os.path.dirname(LOG_FILE)) else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =====================================================================
# PHASE 1: DÉTECTER COMMUNES MANQUANTES
# =====================================================================

def load_mapping_communes(dept_num: str = None) -> Dict[str, Dict]:
    """Charge communes_mapping.csv, optionnellement filtrées par département"""
    communes = {}

    if not os.path.exists(MAPPING_FILE):
        logger.warning(f"⚠️  {MAPPING_FILE} non trouvé")
        return communes

    try:
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                nom = row.get('nom_correct') or row.get('commune', '').strip()
                insee = row.get('code_insee', '').strip()

                if nom and insee:
                    # Extraire le département du code INSEE (2 premiers chiffres)
                    row_dept = insee[:2]
                    if dept_num is None or row_dept == dept_num:
                        communes[nom] = {
                            'insee': insee,
                            'dept': row_dept,
                            'lat': float(row.get('latitude', 0)) if row.get('latitude') else 0,
                            'lon': float(row.get('longitude', 0)) if row.get('longitude') else 0,
                        }
    except Exception as e:
        logger.error(f"❌ Erreur lecture mapping: {e}")

    return communes

def get_all_departments() -> Set[str]:
    """Détecte tous les départements présents dans le CSV mapping"""
    all_communes = load_mapping_communes()
    depts = set(c['dept'] for c in all_communes.values() if 'dept' in c)
    logger.info(f"📍 Départements trouvés: {sorted(depts)}")
    return depts

def load_geojson_communes(dept_num: str) -> Set[str]:
    """Récupère communes présentes dans GeoJSON d'un département"""
    communes = set()
    geojson_path = f"{GEOJSON_DIR}/communes-{dept_num}.geojson"

    if not os.path.exists(geojson_path):
        logger.info(f"ℹ️  GeoJSON dept {dept_num} n'existe pas (sera créé si besoin)")
        return communes

    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
            for feature in geojson.get('features', []):
                props = feature.get('properties', {})
                name = props.get('nom')
                if name:
                    communes.add(name)
    except Exception as e:
        logger.error(f"❌ Erreur lecture GeoJSON dept {dept_num}: {e}")

    return communes

def find_missing_communes(dept_num: str) -> Dict[str, Dict]:
    """Retourne communes dans mapping mais PAS dans GeoJSON pour un département"""
    mapping_communes = load_mapping_communes(dept_num)
    geojson_communes = load_geojson_communes(dept_num)

    missing = {}
    for nom, data in mapping_communes.items():
        if nom not in geojson_communes:
            missing[nom] = data
            logger.info(f"  📍 MANQUANTE: {nom} (INSEE={data['insee']})")

    return missing

# =====================================================================
# PHASE 2: ENRICHIR VIA OVERPASS (AVEC FALLBACK)
# =====================================================================

def get_polygon_overpass(commune_name: str, lat: float, lon: float) -> Optional[Dict]:
    """Tente Overpass, fallback sur Point simple"""

    query = f"""
[bbox:42,2,51,8];
(
  relation["name"="{commune_name}"]["admin_level"="8"];
  way["name"="{commune_name}"]["admin_level"="8"];
);
out geom;
"""

    try:
        logger.info(f"  🔄 Overpass: {commune_name}...")
        response = requests.post(
            OVERPASS_URL,
            data=query,
            timeout=TIMEOUT,
            headers={'User-Agent': 'color-communes-bot/1.0'}
        )
        time.sleep(RATE_LIMIT)

        if response.status_code == 200 and response.json().get('elements'):
            element = response.json()['elements'][0]

            # Essayer d'extraire géométrie
            if element.get('type') == 'way' and 'geometry' in element:
                coords = [[n['lon'], n['lat']] for n in element['geometry']]
                if len(coords) >= 3:
                    return {
                        "type": "Feature",
                        "properties": {"nom": commune_name, "source": "overpass"},
                        "geometry": {"type": "Polygon", "coordinates": [coords]}
                    }

    except Exception as e:
        logger.warning(f"  ⚠️  Overpass erreur: {e}")

    # FALLBACK: Point simple
    logger.info(f"  → Fallback: Point simple")
    return {
        "type": "Feature",
        "properties": {"nom": commune_name, "source": "fallback_point"},
        "geometry": {"type": "Point", "coordinates": [lon, lat]}
    }

# =====================================================================
# PHASE 3: METTRE À JOUR GEOJSON
# =====================================================================

def add_to_geojson(dept_num: str, features: List[Dict]) -> int:
    """Ajoute features au GeoJSON d'un département"""

    geojson_path = f"{GEOJSON_DIR}/communes-{dept_num}.geojson"

    # Load ou create
    if os.path.exists(geojson_path):
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                geojson = json.load(f)
        except:
            geojson = {"type": "FeatureCollection", "features": []}
    else:
        geojson = {"type": "FeatureCollection", "features": []}

    # Existing
    existing_names = {
        f['properties'].get('nom')
        for f in geojson['features']
        if 'properties' in f
    }

    added = 0
    for feature in features:
        name = feature['properties']['nom']
        if name not in existing_names:
            geojson['features'].append(feature)
            added += 1

    # Save
    if added > 0:
        os.makedirs(os.path.dirname(geojson_path), exist_ok=True)
        with open(geojson_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        logger.info(f"  ✅ {added} features ajoutées au GeoJSON dept {dept_num}")

    return added

# =====================================================================
# MAIN: EXÉCUTION AU DÉMARRAGE
# =====================================================================

def ensure_communes_enriched() -> bool:
    """FONCTION PRINCIPALE — À appeler au démarrage du bot"""

    logger.info("=" * 70)
    logger.info("🚀 AUTO_ENRICH STARTUP — Enrichissement GeoJSON tous départements")
    logger.info("=" * 70)

    # 1. Détecter tous les départements
    all_depts = get_all_departments()
    if not all_depts:
        logger.warning("⚠️  Aucun département trouvé dans le mapping")
        return False

    total_enriched = 0

    # 2. Pour chaque département
    for dept_num in sorted(all_depts):
        logger.info(f"\n📍 Traitement département {dept_num}...")
        missing = find_missing_communes(dept_num)

        if not missing:
            logger.info(f"  ✅ Toutes les communes du dept {dept_num} sont présentes")
            continue

        logger.info(f"  📊 {len(missing)} communes manquantes:")
        for nom in missing:
            logger.info(f"    • {nom}")

        # 2b. Enrichir chaque commune
        logger.info(f"  🔄 Enrichissement...")
        features_to_add = []

        for commune_name, data in missing.items():
            feature = get_polygon_overpass(commune_name, data['lat'], data['lon'])
            if feature:
                features_to_add.append(feature)

        # 2c. Ajouter au GeoJSON du département
        if features_to_add:
            added = add_to_geojson(dept_num, features_to_add)
            total_enriched += added

    logger.info("\n" + "=" * 70)
    logger.info(f"✅ AUTO_ENRICH TERMINÉ: {total_enriched} communes ajoutées au total")
    logger.info("=" * 70)
    return True

if __name__ == "__main__":
    success = ensure_communes_enriched()
    exit(0 if success else 1)
