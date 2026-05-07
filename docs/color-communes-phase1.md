---
title: "Color_communes — Phase 1 Setup Docker Synology"
tags: [color-communes, docker, synology, setup, proj1-color]
date: 2026-04-29
1=: informatique
2=: Docker
3=: procédure locale
4=: procédure
---

# Phase 1 — Setup Docker Synology

## Fichiers générés

> Tous les fichiers de déploiement sont dans `raw/color-communes/` :
> - `.env` — tokens + config (⚠️ sécurisé)
> - `requirements.txt` — dépendances Python pinned
> - `Dockerfile` — image Python 3.12-slim
> - `docker-compose.yml` — orchestration container
> - `PHASE1_INSTRUCTIONS.md` — guide détaillé

## Checklist Phase 1

### ✅ Fichiers créés localement
- [x] `.env` avec token Telegram + config
- [x] `requirements.txt` pinned
- [x] `Dockerfile` Python 3.12-slim + GDAL
- [x] `docker-compose.yml` avec volumes `/data`

### À faire sur Synology

```bash
# 1. SSH sur Synology
ssh admin@synology.local

# 2. Créer structure de dossiers
mkdir -p /volume1/docker/color-communes/data
mkdir -p /volume1/docker/color-communes/geojson_cache

# 3. Copier les 4 fichiers (depuis PC)
scp raw/color-communes/{.env,requirements.txt,Dockerfile,docker-compose.yml} \
    admin@synology.local:/volume1/docker/color-communes/

# 4. Compléter .env avec ton User ID Telegram
nano /volume1/docker/color-communes/.env
# TELEGRAM_USER_ID=<ta_valeur>

# 5. Lancer le container
cd /volume1/docker/color-communes
docker compose up -d --build

# 6. Vérifier démarrage
docker compose logs -f color-communes
```

## Tokens & Secrets

| Variable | Valeur | Localisation |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `8641037757:AAEj2XLOm5Lb_XLM3ouCLqLFC7vgw9AK_9k` | `.env` |
| `TELEGRAM_USER_ID` | ❓ *À compléter* | `.env` |
| `NOMINATIM_EMAIL` | `cbtitalia@gmail.com` | `.env` |

> **⚠️ Sécurité** : `.env` est exclu du dépôt Git. Ne jamais commiter les secrets.

## Temps Phase 1

- Préparation fichiers : ✅ **30 min** (déjà fait)
- Déploiement Synology : ~30 min

**Total Phase 1** : ~1h

## Références

- [[color-communes-bot-telegram]] — Détail complet du projet
- [[Informatique/Homelab]] — Architecture Synology
