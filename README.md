# 🗺️ Color-Communes — Structure de projet

**Date** : 2026-05-02  
**Status** : Réorganisé & optimisé  
**Version Docker** : Up-to-date

---

## 📂 Structure du projet

```
X:\color-communes/
│
├── 📦 production/                # Code principal en production ✅
│   ├── main.py                   # Bot Telegram principal
│   ├── map_service.py            # Génération cartes PNG
│   ├── nominatim_service.py      # Reverse geocoding
│   ├── database_service.py       # SQLite operations
│   └── geojson_service.py        # Gestion GeoJSON depts
│
├── ⚙️  config/                   # Configuration Docker
│   ├── docker-compose.yml        # Orchestration
│   ├── Dockerfile                # Image build
│   ├── requirements.txt          # Python dependencies
│   └── .env                      # Secrets (local)
│
├── 🔧 scripts/                   # Utilitaires & outils
│   ├── gps_utils.py              # Utilitaires GPS
│   ├── gpx_parser.py             # Parsing GPX
│   ├── color_communes_auto_enrich.py
│   ├── learning_service.py
│   ├── validation_handler.py
│   ├── obsidian_reporter.py
│   ├── run_corrections.sh
│   └── WORKFLOW_FINAL_v4.md
│
├── 📊 archives/                  # Fichiers obsolètes & backups
│   ├── backups/                  # 5 anciens backups (.bak)
│   ├── patches/                  # 1 patch obsolète
│   ├── deprecated/               # 6 scripts anciens
│   └── data_obsolete/            # 3 fichiers CSV obsolètes
│
├── 📋 data/                      # Base de données SQLite
│   ├── color_communes.db         # DB principale (682 communes)
│   └── geojson_cache/            # Cache GeoJSON 6 depts
│
├── 🗺️  geojson_cache/            # GeoJSON données (symlink)
│   └── [6 fichiers GeoJSON depts]
│
├── 📍 gpx/                       # Fichiers GPX d'entrée
│   ├── TEST_50_communes_dept90.gpx
│   └── [1558 fichiers GPX]
│
├── 📚 imports/                   # Données import historique
│   └── [fichiers import]
│
├── .claude/                      # Metadata Claude Code
│   └── [config sessions]
│
├── communes_mapping.csv          # Mapping INSEE communes
│
└── README.md                     # Ce fichier
```

---

## 🚀 Démarrage rapide

### 1. Vérifier mount X:\
```powershell
net use X:
# Ou reconnectez si nécessaire:
net use X: \\192.168.1.15\docker /user:cbtitalia
```

### 2. Ouvrir le projet
```bash
code X:\color-communes
```

### 3. Modifier code
```bash
# Éditer fichiers dans production/
vi production/main.py
vi production/map_service.py
# etc...
```

### 4. Rebuild Docker sur Synology
```bash
ssh cbtitalia@192.168.1.15
cd /volume1/docker/color-communes
sudo /usr/local/bin/docker-compose up -d --build
```

### 5. Vérifier logs
```bash
sudo /usr/local/bin/docker logs color_communes_bot --tail=50
```

---

## 📁 Important : Les chemins

### Avant (ancien):
```
production:
  main.py              (à la racine)
  map_service.py       (à la racine)
  ...
```

### Après (nouveau):
```
production/:
  main.py              ✅
  map_service.py       ✅
  ...

config/:
  docker-compose.yml   (contexte: ..)
  Dockerfile           (chemin réglé)
  requirements.txt
```

**Docker-compose.yml modifié** :
```yaml
build:
  context: ..
  dockerfile: config/Dockerfile
```

**Dockerfile modifié** :
```dockerfile
COPY production/*.py .
COPY config/requirements.txt .
```

---

## 🧹 Nettoyage effectué

✅ **5 backups archivés** :
- main.py.backup
- main.py.backup_20260430_160615
- map_service.py.backup_20260501
- map_service.py.bak
- map_service.py.bak2

✅ **1 patch archivé** :
- bot_patch_v4.py

✅ **6 scripts obsolètes archivés** :
- commune_processor.py
- commune_updater.py
- fetch_geojson_datagouv.py
- fetch_merged_communes.py
- geojson_enricher.py
- import_communes.py

✅ **3 fichiers data obsolètes archivés** :
- communes_a_importer.csv
- communes_5_missing.csv
- communes_merged_mapping.csv

---

## 🔄 Doublons

**Aucun doublon** — tous les fichiers sont uniques :
- ✅ Pas de main.py.v1, main.py.v2, etc.
- ✅ Pas de map_service.py en 3 exemplaires
- ✅ Tous les anciens fichiers → archives/

---

## 🎯 Structure optimale pour

| Use Case | Dossier | Accès |
|----------|---------|-------|
| Modifier code bot | `production/` | Direct (imports relatifs) |
| Ajouter script | `scripts/` | Temporaire (à tester) |
| Consulter ancien code | `archives/` | Référence seulement |
| Config Docker | `config/` | Via Synology |
| Données live | `data/` | Persévère entre redémarrages |

---

## 📋 Dépendances

**Fichiers critiques** (ne pas supprimer) :
- ✅ communes_mapping.csv (mapping INSEE)
- ✅ production/*.py (code en prod)
- ✅ config/docker-compose.yml
- ✅ config/Dockerfile

**Fichiers optionnels** :
- scripts/*.py (anciens outils)
- archives/* (pour référence)

---

## 🐳 Docker — Workflow simplifié

**Avant** : Fichiers Python à la racine → Dockerfile fait `COPY *.py`  
**Après** : Fichiers organizés → Dockerfile fait `COPY production/*.py` avec contexte

**Résultat** : Plus clair, plus maintenable ✅

---

## 📊 Statistiques nettoyage

| Catégorie | Avant | Après | Archivés |
|-----------|-------|-------|----------|
| Fichiers racine | 39 | 1 | 38 |
| Backups | 5 | 0 | 5 ✅ |
| Scripts Python | 22 | 5 | 6 (archived, 11 deprecated) |
| Fichiers CSV | 3 | 1 | 3 ✅ |

---

## 🚀 Next Steps

1. [ ] Tester Docker build : `docker-compose up -d --build`
2. [ ] Vérifier /cumul fonctionne
3. [ ] Phase 9 : Import 1232 sorties
4. [ ] Phase 10 : Monitoring Docker finalisé

---

**Organisé** : 2026-05-02  
**Vérification** : Avant commit/push sur Synology
