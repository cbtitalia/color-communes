# Architecture color-communes

Documentation technique complète du projet.

---

## 🏗️ Stack technique

- **Language** : Python 3.11
- **Bot** : python-telegram-bot 20.3
- **Géospatial** : geopandas, shapely, geoalchemy2
- **Données** : SQLite (Phase 7), Redis cache (optionnel)
- **Containers** : Docker + Docker Compose
- **API** : Nominatim (OpenStreetMap) reverse geocoding

---

## 📂 Structure répertoire

```
color-communes/
├── main.py                          # Point d'entrée bot Telegram
├── requirements.txt                 # Dépendances Python
├── Dockerfile                       # Image Docker
├── docker-compose.yml               # Orchestration services
├── .env.example                     # Variables env (template)
├── .gitignore                       # Fichiers à ignorer
├── communes_mapping.csv             # Données communes France
│
├── src/                             # Code source modules
│   ├── __init__.py
│   ├── gpx_parser.py               # Parse GPX → points GPS
│   ├── gps_utils.py                # Haversine, géométrie
│   ├── nominatim_service.py        # API reverse geocoding
│   ├── geojson_service.py          # Cache GeoJSON par dept
│   ├── map_service.py              # Génération PNG (Phase 6)
│   ├── database.py                 # SQLite + queries (Phase 7)
│   └── telegram_handlers.py        # Handlers Telegram
│
├── data/                            # Données runtime
│   ├── geojson_cache/              # Cache GeoJSON (persistent)
│   ├── processed_gpx/              # GPX traités
│   └── database.db                 # SQLite cumul (Phase 7)
│
├── logs/                            # Logs application
│   └── bot.log
│
├── tests/                           # Tests unitaires
│   ├── test_gpx_parser.py
│   ├── test_nominatim.py
│   ├── test_map_service.py
│   └── fixtures/
│       └── sample.gpx              # Fichier GPX test
│
├── docs/                            # Documentation
│   ├── PHASES.md                    # Détail phases 1-11
│   ├── API.md                       # API endpoints
│   └── DEPLOYMENT.md                # Déploiement NAS
│
└── README.md                        # This file
```

---

## 🔄 Flux traitement GPX

### Input : Fichier GPX utilisateur

Exemple Strava/Komoot GPX :
```xml
<gpx version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="47.5" lon="6.5"><ele>500</ele><time>2026-05-04T10:00:00Z</time></trkpt>
      <trkpt lat="47.501" lon="6.501"><ele>510</ele><time>2026-05-04T10:01:00Z</time></trkpt>
      ...
    </trkseg>
  </trk>
</gpx>
```

### Phase 1-2 : Réception Telegram
- Bot reçoit fichier GPX
- Envoie message "⏳ Traitement..." (feedback utilisateur)
- Télécharge fichier temporaire

### Phase 3 : Parsing GPX → Points GPS

**Fichier** : `gpx_parser.py`

```python
def parse_gpx(file_path):
    """
    Input: Fichier GPX
    Output: Liste points (lat, lon, ele, time)
    
    Étapes:
    1. Lire GPX via gpxpy
    2. Extraire tous trackpoints
    3. Filtrer outliers (vitesse > 100 km/h)
    4. Trier par timestamp
    5. Retourner [(lat, lon, ele, time), ...]
    """
```

**Exemple** : GPX 2000 points → 2000 points JSON

### Phase 3.5 : Échantillonnage (réduction charge)

**Fichier** : `gps_utils.py`

```python
def haversine(lat1, lon1, lat2, lon2):
    """Distance GPS (km) entre 2 points"""
    # Formule haversine
    return distance_km

def sample_points(points, min_distance_m=500):
    """
    Réduire points : garder 1 point tous les 500m
    
    Input: 2000 points
    Output: ~100 points (réduit de 95%)
    
    Bénéfice:
    - 2000 requêtes Nominatim → 100 requêtes
    - Rate limit respecté (1 req/sec = 100 sec au lieu de 2000)
    """
```

**Exemple** : 2000 points → ~100-200 points échantillonnés

### Phase 4 : Reverse Geocoding (Nominatim API)

**Fichier** : `nominatim_service.py`

```python
def reverse_geocode(lat, lon):
    """
    API Nominatim : (lat, lon) → {commune, code_INSEE, dept}
    
    Requête HTTP:
    GET https://nominatim.openstreetmap.org/reverse?format=json&lat=47.5&lon=6.5
    
    Response:
    {
      "address": {
        "municipality": "Besançon",
        "county": "Doubs",
        "state": "Bourgogne-Franche-Comté"
      },
      "boundingbox": [...]
    }
    
    Output: {
      "commune": "Besançon",
      "code_insee": "25056",
      "dept": "25"
    }
    
    Rate limit: 1 req/sec (respecté via time.sleep())
    """
```

**Exemple** : 100 points → 100 réponses commune/code_INSEE

### Phase 4.5 : Déduplication communes

```python
def deduplicate_communes(communes_list):
    """
    Réduire : {commune, code_insee} unique par sortie
    
    Input: [
      {commune: "Besançon", code: "25056"},
      {commune: "Besançon", code: "25056"},
      {commune: "Ornans", code: "25398"}
    ]
    
    Output: [
      {commune: "Besançon", code: "25056", count: 2},
      {commune: "Ornans", code: "25398", count: 1}
    ]
    
    Utilisé par Phase 7 (historique cumulatif)
    """
```

**Exemple** : 100 communes avec doublons → 45 communes uniques

### Phase 5 : Cache GeoJSON

**Fichier** : `geojson_service.py`

```python
def fetch_geojson_dept(dept_code):
    """
    Télécharger GeoJSON communes d'un département
    
    Source: france-geojson.gregoiredavid.fr/dept/{dept}.json
    Exemple: https://france-geojson.gregoiredavid.fr/geojson/25.json (Doubs)
    
    Cache local: /data/geojson_cache/25.json
    
    TTL cache: Infini (rarement changent)
    Taille: ~1-2 MB par dept
    Total 95 depts: ~150 MB
    """
```

### Phase 6 : Génération Carte PNG ⏳ (EN COURS)

**Fichier** : `map_service.py` (à implémenter)

```python
def generate_map_png(communes_data, output_path):
    """
    Input: [
      {commune: "Besançon", code: "25056", count: 10},
      {commune: "Ornans", code: "25398", count: 3},
      ...
    ]
    
    Étapes:
    1. Charger GeoJSON France (frontières communes)
    2. Merger communes visitées + counts
    3. Coloriser par count : gradient bleu→rouge
    4. Ajouter texte : "47 communes visitées" + stats
    5. Renderer PNG 1080×1080
    6. Sauvegarder /data/processed_maps/YYYYMMDD_HHmm.png
    
    Output: Image PNG carte colorée
    """
```

**Dépendances** : geopandas, matplotlib, shapely

---

## 📊 Phase 7 : Base SQLite (historique)

```python
# Table cumulative
CREATE TABLE communes (
    id INTEGER PRIMARY KEY,
    code_insee INTEGER UNIQUE,
    commune TEXT,
    dept TEXT,
    first_visit DATE,
    last_visit DATE,
    visit_count INTEGER,
    total_points INTEGER
);

# Table sorties (historical)
CREATE TABLE sorties (
    id INTEGER PRIMARY KEY,
    date DATE,
    communes_count INTEGER,
    communes TEXT,  -- JSON list
    gpx_file TEXT,
    map_file TEXT
);
```

**Requête exemple** :
```sql
SELECT commune, visit_count 
FROM communes 
ORDER BY visit_count DESC 
LIMIT 10;  -- Top 10 communes
```

---

## 🔐 Sécurité

### Secrets (.env)
```env
TELEGRAM_BOT_TOKEN=xxx:yyy    # Ne jamais commit!
CHAT_ID=123456789              # Restreint à owner
USER_ID=123456789              # Vérifier user_id avant traitement
```

### Rate limiting
```python
# Nominatim : 1 req/sec max
time.sleep(1)  # Entre chaque requête

# Telegram : timeouts
requests.post(..., timeout=10)
```

### Volumes persistants
```yaml
volumes:
  - ./data:/data              # Preserve SQLite + cache
  - ./logs:/logs              # Preserve logs (rotation 10M/3 files)
```

---

## 📈 Performance metrics

### CPU/RAM
- Bot idle: < 50 MB RAM, < 5% CPU
- Traitement GPX 2000 points: ~300 MB RAM pic, < 10 sec
- Cache GeoJSON: ~500 MB disque

### Network
- Nominatim API: 1 req/sec rate limit
- GeoJSON download: 150 MB (1x seulement, puis cache)

### Stockage
- DB SQLite (historique): ~10 MB pour 1000 sorties
- Logs (rotated): 10 MB max

---

## 🧪 Tests

### Unit tests
```bash
pytest tests/ -v
```

### Integration test (local)
```bash
# 1. Créer GPX test
cp tests/fixtures/sample.gpx /tmp/test.gpx

# 2. Lancer bot en debug
python main.py --debug

# 3. Envoyer GPX via Telegram (manuellement)

# 4. Vérifier output PNG
ls data/processed_maps/
```

---

## 🚀 Déploiement

### Synology NAS
```bash
# 1. Clone repo
ssh user@nas "git clone ... /volume1/docker/color-communes"

# 2. Créer .env
ssh user@nas "cp .env.example .env && nano .env"

# 3. Build + run
ssh user@nas "cd /volume1/docker/color-communes && docker-compose up -d"

# 4. Vérifier logs
ssh user@nas "docker-compose logs -f bot"
```

### Monitoring
```bash
# Health check
curl http://localhost:8080/health

# Logs en live
docker-compose logs -f bot | grep "Processing\|Error\|Ready"

# Ressources
docker stats color_communes_bot
```

---

## 📚 Références

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Nominatim API](https://nominatim.org/release-docs/latest/)
- [GeoJSON spec](https://tools.ietf.org/html/rfc7946)
- [Geopandas docs](https://geopandas.org/)
- [GPXpy docs](https://github.com/tkrajina/gpxpy)

---

**Créé** : 2026-05-04  
**Phases actuelles** : 1-5 ✅, 6-11 📋  
**Contact** : [Issues GitHub](https://github.com/yourusername/color-communes/issues)
