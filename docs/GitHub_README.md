# color-communes

Telegram bot qui transforme vos fichiers GPX en cartes colorées des communes françaises visitées à vélo.

**[Demo](#demo) • [Installation](#installation) • [Architecture](#architecture) • [Phases](#phases) • [Contributing](#contributing)**

---

## 🚀 Démarrage rapide

### Prérequis
- Docker + Docker Compose
- Token Telegram ([@BotFather](https://t.me/botfather))
- Python 3.11+

### Installation 5 min

```bash
git clone https://github.com/yourusername/color-communes.git
cd color-communes

# Créer .env
cp .env.example .env
# Éditer : TELEGRAM_BOT_TOKEN, CHAT_ID

# Déployer
docker-compose up -d

# Tester
curl http://localhost:8080/health
```

---

## 📋 Fonctionnement

1. **Envoyez un fichier GPX** via Telegram
2. **Bot traite** : parsing points GPS + reverse geocoding
3. **Reçoit une carte PNG** : communes colorées par nb passages

### Formats supportés
- ✅ Garmin
- ✅ Strava
- ✅ Komoot

### Exemple usage

```
[Envoi GPX dans chat Telegram]
Bot: ⏳ Traitement en cours...
Bot: [Image carte PNG]
```

---

## 🏗️ Architecture

### Services Docker
- **bot** — Python 3.11 + python-telegram-bot
- **nominatim** — Reverse geocoding (optionnel, API publique par défaut)
- **redis** — Cache (optionnel)

### Flux de données

```
GPX (utilisateur)
    ↓ [Parsing]
Points GPS (lat/lon)
    ↓ [Échantillonnage 500m]
Points filtrés (réduction charge)
    ↓ [Reverse Geocoding Nominatim]
Communes (code INSEE + nom)
    ↓ [Déduplication]
Communes uniques
    ↓ [GeoJSON + Geopandas]
Carte PNG colorée
    ↓
[Telegram bot envoie image]
```

### Modules

| Module | Rôle | Dépendances |
|---|---|---|
| `main.py` | Bot Telegram principal | python-telegram-bot |
| `gpx_parser.py` | Parse GPX, échantillonne points | gpxpy |
| `nominatim_service.py` | Reverse geocoding (API OSM) | requests |
| `geojson_service.py` | Télécharge/cache GeoJSON | requests |
| `map_service.py` | Génère carte PNG (Phase 6) | geopandas, matplotlib |
| `gps_utils.py` | Utilitaires géométrie | math |

---

## 📊 Phases de développement

| Phase | Statut | Tâche | Durée |
|---|---|---|---|
| 1 | ✅ | Docker + secrets | 1h |
| 2 | ✅ | Bot Telegram base | 30min |
| 3 | ✅ | Parsing GPX | 1h |
| 4 | ✅ | Reverse geocoding | 1h30 |
| 5 | ✅ | Cache GeoJSON | 1h |
| **6** | **⏳** | **Carte PNG** | **3h** |
| 7 | 📋 | Base SQLite (historique) | 2h |
| 8 | 📋 | Commandes /cumul /stats | 1h |
| 9 | 📋 | Import historique (1232 sorties) | 2h |
| 10 | 📋 | Monitoring Docker | 1h |
| 11 | 📋 | Tests & finitions | 1h |

**État actuel** : Phase 5 ✅ (phases 6-11 en backlog)

---

## 🔧 Configuration

### Variables d'environnement (`.env`)

```env
# Telegram
TELEGRAM_BOT_TOKEN=xxx:yyy
CHAT_ID=123456789
USER_ID=123456789          # Restreindre à owner

# Nominatim (optionnel, API publique par défaut)
NOMINATIM_URL=https://nominatim.openstreetmap.org/reverse
NOMINATIM_RATE_LIMIT=1    # req/sec

# Données
DATA_DIR=/data
LOG_DIR=/logs
COMMUNES_CSV=/app/communes_mapping.csv

# Logs
LOG_LEVEL=INFO
```

### Docker Compose

```yaml
version: '3.8'
services:
  bot:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - CHAT_ID=${CHAT_ID}
      - NOMINATIM_URL=${NOMINATIM_URL}
    volumes:
      - ./data:/data
      - ./logs:/logs
    restart: unless-stopped
```

---

## 📦 Dépendances

```
python-telegram-bot==20.3
gpxpy==1.6.2
requests==2.31.0
geopandas==0.13.2
matplotlib==3.7.1
shapely==2.0.1
```

Voir `requirements.txt` pour versions pinned.

---

## 🧪 Tests

```bash
# Test parsing GPX
python -m pytest tests/test_gpx_parser.py

# Test Nominatim
python -m pytest tests/test_nominatim.py

# Test bot (local)
python main.py --debug
```

---

## 🚀 Déploiement

### Production (Synology NAS)

```bash
ssh user@nas "cd /volume1/docker/color-communes && docker-compose up -d"
```

### Monitoring

```bash
docker-compose logs -f bot
```

---

## 📈 Performances

| Métrique | Valeur |
|---|---|
| Parsing GPX | < 5 sec (1000 points) |
| Reverse geocoding | 1 req/sec (rate limit Nominatim) |
| Génération PNG | ~2-5 sec |
| Total (end-to-end) | ~10-15 sec |
| RAM bot | ~150 MB |
| Cache GeoJSON | ~500 MB (70 fichiers depts) |

---

## 🐛 Troubleshooting

### Bot ne répond pas

```bash
# Vérifier logs
docker-compose logs bot | tail -20

# Vérifier token
echo $TELEGRAM_BOT_TOKEN
```

### Nominatim timeout

- Vérifier rate limit : 1 req/sec max
- Fallback API publique : `https://nominatim.openstreetmap.org/reverse`

### Génération PNG échoue

- Phase 6 en cours (non implémentée)
- Dépendances geopandas/GDAL à installer

---

## 📝 Licence

MIT — Voir `LICENSE`

---

## 🤝 Contributing

Les contributions sont bienvenues ! Forker → créer branche → submit PR.

### Avant PR
1. Tests passants : `pytest tests/`
2. Code style : `black .`
3. Linting : `flake8`

---

## 📞 Support

- **Issues** : GitHub Issues
- **Questions** : Telegram [@yourusername](https://t.me/yourusername)
- **Docs complètes** : [ARCHITECTURE.md](./ARCHITECTURE.md)

---

**Stars** ⭐ bienvenues ! 

*Fait avec ❤️ pour les cyclistes*
