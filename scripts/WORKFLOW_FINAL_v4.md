# Workflow Final v4 — Color Communes

**Date** : 30/04/2026  
**Statut** : 🟢 Prêt pour test final  
**Objectif** : Ajouter 5 communes (Rougegoutte, Faverois, Menoncourt, Meroux, Grandvillars) au bot

---

## 📋 Checklist Rapide

### ✅ DÉJÀ FAIT
- [x] Bot rebuilding avec patch generation CSV communes_nominatim_found
- [x] Script v3 créé (Phase 2 report parser)
- [x] Script v4 créé (Full auto workflow)
- [x] Script fix_nominatim_csv créé (coords enrichment)
- [x] Documentation mise à jour

### ⏳ À FAIRE

**1. Upload scripts sur Synology**
```bash
scp auto_enrich_geojson_v4.py cbtitalia@192.168.1.15:/volume1/docker/color-communes/
scp fix_nominatim_csv.py cbtitalia@192.168.1.15:/volume1/docker/color-communes/
```

**2. Importer GPX dans le bot**
- Envoie `2026_07_Des_bosses.gpx` au bot Telegram
- Bot génère `communes_nominatim_found_YYYYMMDD_HHMMSS.csv`

**3. Exécuter enrichissement**
```bash
ssh cbtitalia@192.168.1.15

cd /volume1/docker/color-communes

# Enrichir coordonnées
python3 fix_nominatim_csv.py

# Ajouter au GeoJSON
python3 auto_enrich_geojson_v4.py

# Vérifier résultats
cat communes_mapping.csv | grep -E "Rougegoutte|Faverois|Menoncourt|Meroux|Grandvillars"

# Rebuild container
docker-compose down
docker-compose up --build -d
```

**4. Tester et vérifier**
- Importer à nouveau un GPX
- Vérifier que les 5 communes apparaissent avec coordonnées valides
- Vérifier que la carte affiche les 5 communes

---

## 🔑 Fichiers clés

| Fichier | Chemin | Rôle |
|---------|--------|------|
| auto_enrich_geojson_v4.py | D:\Obsidian\Brain_Stan\ | Script enrichissement full auto |
| fix_nominatim_csv.py | D:\Obsidian\Brain_Stan\ | Correcteur coordonnées |
| Color_communes_Phase2_Integration.md | wiki/Informatique/Docker/ | Documentation complète |
| communes_mapping.csv | /volume1/docker/color-communes/ | Base communes mappées |
| communes_nominatim_found_*.csv | /volume1/docker/color-communes/data/ | CSV généré par bot |

---

## 📊 Structure du workflow

```
Import GPX
    ↓
Bot traite (Nominatim)
    ↓
Bot génère communes_nominatim_found_*.csv
    ↓
fix_nominatim_csv.py (enrichit coords)
    ↓
auto_enrich_geojson_v4.py
  ├─ Ajoute à communes_mapping.csv
  └─ Ajoute au GeoJSON dept 90
    ↓
docker-compose rebuild
    ↓
Bot prêt avec 5 communes visibles
```

---

## ✨ Points importants

1. **v4 est 100% automatisé** après l'import GPX
2. **fix_nominatim_csv doit s'exécuter AVANT v4** (sinon coords = 0,0)
3. **Rebuild obligatoire** après enrichissement GeoJSON
4. **Test avec 2026_07_Des_bosses.gpx** qui contient les 5 communes cibles

---

## 🎯 Critères de succès

- [ ] 5 communes visibles dans communes_mapping.csv avec coords valides
- [ ] 5 communes dans GeoJSON departement_90.geojson
- [ ] Bot accepte les communes sans erreur (statut: nominatim)
- [ ] Carte bot affiche les 5 communes correctement

---

**Créé par** : Claude Code  
**Pour continuer** : Lire ce fichier + Color_communes_Phase2_Integration.md
