---
title: "Color_communes — Architecture & Flux de traitement"
tags: [color-communes, architecture, bot, telegram, gpx, python, proj1-color]
date: 2026-04-29
1=: informatique
2=: Python
3=: doc projet
4=: note documentaire
---

# Color_communes — Architecture & Flux

## État actuel (2026-04-29)

**Phases complétées :** 1-8 / 11  
**Temps investi :** ~11h  
**Status :** Bot Telegram live, cartes PNG colorisées, base SQLite cumulative, commandes avancées ✅

---

## Flux de traitement GPX

```
1. Utilisateur envoie GPX dans Telegram
          ↓
2. Bot télécharge fichier GPX
          ↓
3. 📍 PARSING GPX (Phase 3: gps_utils.py + gpx_parser.py)
   • Lecture avec gpxpy
   • Extraction points GPS (lat, lon)
   • Échantillonnage haversine : 1 point / 500m
          ↓
4. 🏘️ REVERSE GEOCODING (Phase 4: nominatim_service.py)
   • API Nominatim : lat/lon → commune
   • Extraction code INSEE + nom
   • Rate limit respecté : 1 req/sec
   • Déduplication : une commune = une entrée
          ↓
5. 🗺️ CACHE GEOJSON (Phase 5: geojson_service.py)
   • Identification départements (depuis INSEE)
   • Téléchargement GeoJSON par département
   • Cache local : /data/geojson_cache/
          ↓
6. 🎨 GÉNÉRATION CARTE PNG (Phase 6 - À FAIRE)
   • Colorisation communes selon nb_passages
   • Rendu avec geopandas + matplotlib
   • Export PNG 1080×1080
          ↓
7. 📤 Bot renvoie image PNG dans Telegram
```

---

## Fichiers déployés

### Infrastructure
- **`.env`** — tokens Telegram + config emails
- **`Dockerfile`** — Python 3.12-slim + GDAL
- **`docker-compose.yml`** — volumes `/data`, env_file `.env`
- **`requirements.txt`** — dépendances pinned

### Code bot
- **`main.py`** — bot Telegram principal + handlers
  - `/start`, `/help` — messages
  - Réception GPX → orchestration phases 3-5
  
### Services (modules)
- **`gps_utils.py`** — haversine(lat1, lon1, lat2, lon2) → distance m
- **`gpx_parser.py`** — GpxParser.parse() → points GPS échantillonnés
- **`nominatim_service.py`** — NominatimService.reverse_geocode() → communes
- **`geojson_service.py`** — GeoJsonService.get_geojson_for_communes() → cache

---

## Configuration

| Clé | Valeur | Source |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `8641037757:AAEj...` | `.env` |
| `TELEGRAM_USER_ID` | `8137882123` | `.env` |
| `NOMINATIM_EMAIL` | `cbtitalia@gmail.com` | `.env` |
| `DATABASE_PATH` | `/data/color_communes.db` | `.env` |
| `GEOJSON_CACHE_DIR` | `/data/geojson_cache` | `.env` |
| Échantillonnage GPX | 500 mètres | `gpx_parser.py` |
| Rate limit Nominatim | 1 req/sec | `nominatim_service.py` |

---

## Données du bot

**User ID filtré :** 8137882123 (accès restreint au propriétaire)

**Communes historiques :** 1 232 sorties Strava (2012→2026)

---

## Phases restantes

| # | Tâche | Temps | Fichiers | Notes | Statut |
|---|---|---|---|---|---|
| 6 | Génération carte PNG | ~3h | `map_service.py` + `main.py` | geopandas + matplotlib | ✅ FAIT |
| 7 | Base SQLite cumulative | ~3h | `database_service.py` + `main.py` | communes cumulées + doublons | ✅ FAIT |
| 8 | Commandes avancées | ~1h | `main.py` | `/history`, `/compare`, paramètres | 🔴 SUIVANT |
| 9 | Import historique | ~2h | `import_service.py` | 1 232 sorties Strava | ⏳ |
| 10 | Monitoring Docker | ~1h | `syno_monitor.sh` | alerts Telegram | ⏳ |
| 11 | Tests & finitions | ~1h | documentation | QA complet | ⏳ |

---

## Références

- [[color-communes-bot-telegram]] — Specs complètes
- [[Informatique/Color_communes/color-communes-phase1]] — Setup Synology
- [[Informatique/Nominatim]] — API Nominatim
- [[Informatique/Geopandas]] — cartographie Python
