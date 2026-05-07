---
title: "Color_communes — Bot Telegram GPX → Carte communes"
tags: [android, strava, gpx, cartographie, telegram, python, proj1-color]
date: 2026-04-29
type: checklist
statut: actif
1=: velo
2=: Telegram
3=: doc projet
4=: checklist
---

- REF
  - 1= theme:: [[1=velo]] [[1=cartographie]]
  - 2= marque:: [[2=Telegram]] [[2=Python]]
  - 3= systeme:: [[3=doc projet]]
  - 4= type:: [[4=checklist]]

# Color_communes — Bot Telegram GPX → Carte communes

> Bot Python déployé sur Synology.
> Tu envoies un fichier GPX (Komoot, Strava, Garmin) dans Telegram.
> Le bot génère une image PNG de la carte des communes traversées et te la renvoie.
> Mode cumulatif : la carte s'enrichit à chaque nouvelle sortie.

---

![[color-communes-bot-workflow.excalidraw]]

---

## Concept

```
GPX envoyé dans Telegram
    ↓
Bot reçoit le fichier
    ↓
Parse GPX → points GPS (1 point / 500m)
    ↓
Nominatim → communes + codes INSEE
    ↓
GeoJSON département(s) → france-geojson.gregoiredavid.fr
    ↓
geopandas + matplotlib → image PNG
    ↓
Bot renvoie la carte dans Telegram
```

---

## Commandes du bot

| Commande | Action |
|---|---|
| Envoyer 1 GPX | Carte de cette sortie uniquement |
| Envoyer plusieurs GPX | Carte fusionnée |
| `/cumul` | Carte cumulative de toutes les sorties |
| `/stats` | Nombre de communes, départements, sorties |
| `/reset` | Remettre le compteur à zéro |
| `/help` | Aide |

---

## Colorisation

| Passages | Couleur |
|---|---|
| 1 | Jaune pâle `#FFF176` |
| 2–4 | Orange `#FF8F00` |
| 5–9 | Rouge `#E53935` |
| 10+ | Rouge foncé `#B71C1C` |

---

## Récapitulatif tâches

| Phase | Tâches | Temps estimé |
|---|---|---|
| 1 — Setup projet | 4 tâches | ~1h00 |
| 2 — Bot Telegram base | 3 tâches | ~1h00 |
| 3 — Parsing GPX | 3 tâches | ~1h00 |
| 4 — Reverse geocoding Nominatim | 4 tâches | ~2h00 |
| 5 — GeoJSON communes | 3 tâches | ~1h30 |
| 6 — Génération carte PNG | 4 tâches | ~3h00 |
| 7 — Base SQLite cumulative | 4 tâches | ~2h00 |
| 8 — Commandes bot avancées | 3 tâches | ~1h00 |
| 9 — Import historique | 3 tâches | ~2h00 |
| 10 — Déploiement Docker Synology | 3 tâches | ~1h00 |
| 11 — Tests & finitions | 3 tâches | ~1h00 |
| **Total** | **37 tâches** | **~16h30** |

---

## Phase 1 — Setup projet (~1h00)

- [x] Créer le dossier `/volume1/docker/color-communes/` sur Synology `10 min`
- [x] Créer `requirements.txt` (python-telegram-bot, gpxpy, requests, geopandas, matplotlib) `10 min`
- [x] Créer `Dockerfile` Python 3.12-slim `15 min`
- [x] Créer `docker-compose.yml` avec volume pour SQLite et cache GeoJSON `15 min`

> ✅ **Fichiers générés dans `raw/color-communes/`** — voir [[Informatique/Color_communes/color-communes-phase1|Phase 1 Setup]] pour instructions déploiement Synology

---

## Phase 2 — Bot Telegram base (~1h00)

- [ ] Configurer le bot avec le token `8797034358:AAEI63Gr5PNz5uw9JSR0q1-_GCAh-FKE7a8` `10 min`
- [ ] Handler `/start` et `/help` avec message d'accueil `20 min`
- [ ] Handler réception fichier GPX → message "⏳ Traitement en cours..." `30 min`

---

## Phase 3 — Parsing GPX (~1h00)

- [ ] Service `GpxParser` : lire le fichier GPX avec `gpxpy` `20 min`
- [ ] Extraire les points GPS (lat, lon) `10 min`
- [ ] Échantillonnage : garder 1 point tous les 500m (haversine) `30 min`

---

## Phase 4 — Reverse geocoding Nominatim (~2h00)

- [ ] Service `NominatimService` : requête reverse geocoding par point GPS `30 min`
      ```
      GET https://nominatim.openstreetmap.org/reverse
          ?lat=&lon=&format=json&addressdetails=1
      ```
- [ ] Extraire code INSEE (`address.postcode`) + nom commune `20 min`
- [ ] Déduplication : une commune = une seule entrée par GPX `20 min`
- [ ] Respecter le rate limit Nominatim (1 requête/seconde max) `50 min`

---

## Phase 5 — GeoJSON communes (~1h30)

- [ ] Service `GeoJsonService` : identifier les départements concernés depuis les codes INSEE `20 min`
- [ ] Télécharger le GeoJSON de chaque département (france-geojson.gregoiredavid.fr) `30 min`
      ```
      GET https://france-geojson.gregoiredavid.fr/repo/departements/
          {num}-{nom}/communes-{num}-{nom}.geojson
      ```
- [ ] Cache local JSON dans `/data/geojson/` → éviter re-téléchargement `40 min`

---

## Phase 6 — Génération carte PNG (~3h00)

- [ ] Service `MapService` : charger GeoJSON + communes visitées dans geopandas `30 min`
- [ ] Coloriser les communes selon `nb_passages` (palette jaune → rouge) `45 min`
- [ ] Style carte : fond gris clair, contours communes, communes non visitées en blanc `45 min`
- [ ] Export PNG 1080×1080 avec titre + statistiques en overlay `1h00`
      ```
      🚴 {nb_communes} communes | {nb_depts} départements | {date}
      ```

---

## Phase 7 — Base SQLite cumulative (~2h00)

- [ ] Créer schéma SQLite : tables `communes`, `activites`, `geojson_cache` `30 min`
- [ ] Service `DatabaseService` : insérer commune / incrémenter `nb_passages` si existante `45 min`
- [ ] Déduplication activités : ne pas retraiter un GPX déjà importé (hash du fichier) `30 min`
- [ ] Requête : toutes les communes pour le mode `/cumul` `15 min`

---

## Phase 8 — Commandes bot avancées (~1h00)

- [ ] `/cumul` : générer la carte de toutes les communes enregistrées `20 min`
- [ ] `/stats` : afficher stats (communes, départements, sorties, 1ère visite) `20 min`
- [ ] `/reset` : demander confirmation puis vider la base `20 min`

---

## Phase 9 — Import historique (~2h00)

- [ ] Script `import_historique.py` : lire le CSV existant (`extract_CP_commune_INSEE.csv`) `45 min`
- [ ] Peupler la table `communes` depuis l'historique `45 min`
- [ ] Commande `/import` dans le bot : envoyer un fichier JSON d'historique `30 min`

---

## Phase 10 — Déploiement Docker Synology (~1h00)

- [ ] Build image Docker sur Synology `20 min`
      ```bash
      cd /volume1/docker/color-communes && docker compose up -d --build
      ```
- [ ] Vérifier que le bot répond dans Telegram `10 min`
- [ ] Ajouter monitoring Telegram dans `syno_monitor.sh` `30 min`

---

## Phase 11 — Tests & finitions (~1h00)

- [ ] Test complet : envoyer GPX Komoot → vérifier communes + carte reçue `30 min`
- [ ] Test multi-GPX : envoyer 3 fichiers → carte fusionnée `15 min`
- [ ] Test mode cumulatif : 3 envois successifs → carte qui grandit `15 min`

---

## Stack technique

| Composant | Bibliothèque | Rôle |
|---|---|---|
| Bot Telegram | `python-telegram-bot 20.x` | Communication Telegram |
| Parse GPX | `gpxpy` | Lecture fichiers GPX |
| Geocoding | `requests` → Nominatim | Communes depuis GPS |
| Carte | `geopandas` + `matplotlib` | Génération PNG |
| Base données | `sqlite3` (stdlib) | Historique cumulatif |
| Cache GeoJSON | Fichiers JSON locaux | Éviter re-téléchargements |

---

## Références

- [[color-communes-definition]] — Définition complète du projet
- [[colorisation-communes-garmin]] — Pipeline Python existant
- [[pointage-ronfort-monitoring-telegram]] — Bot Telegram Synology (référence)
- [[_index|Index Color_communes]]
