---
title: "Color_communes — Phase 6 : Génération de cartes PNG"
tags: [color-communes, phase6, map-generation, geopandas, matplotlib, geojson]
date: 2026-04-29
1=: informatique
2=: Python
3=: wiki technique
4=: compte-rendu
---

# Color_communes — Phase 6 : Génération de cartes PNG

## Statut
✅ **COMPLÉTÉE** — 2026-04-29

## Objectif
Transformer les communes détectées (via reverse geocoding Nominatim) en cartes PNG colorisées affichant:
- Les communes visitées colorées selon le nombre de passages
- Légende de colorisation
- Statistiques (nombre de communes, départements)

## Architecture et flux

```
GPX (utilisateur)
    ↓
[Phase 3] Parsing GPX → points GPS échantillonnés
    ↓
[Phase 4] Reverse geocoding Nominatim → communes (nom, INSEE, dept)
    ↓
[Phase 5] GeoJSON cache → données cartographiques
    ↓
[Phase 6] Génération carte PNG
    │
    ├─ Charger GeoDataFrame depuis GeoJSON
    ├─ Matcher communes Nominatim avec communes GeoJSON (exact + normalisé)
    ├─ Coloriser selon nombre de passages:
    │  ├─ 🟡 Jaune (#FFF176) : 1 passage
    │  ├─ 🟠 Orange (#FF8F00) : 2-4 passages
    │  ├─ 🔴 Rouge (#E53935) : 5-9 passages
    │  ├─ 🔴🔴 Rouge foncé (#B71C1C) : 10+ passages
    │  └─ ⚪ Blanc (#FFFFFF) : Non visitées
    ├─ Ajouter légende et statistiques
    └─ Exporter PNG 1080×1080 (100 dpi)
    ↓
📤 Envoyer PNG via Telegram
```

## Fichiers implémentés

### Code principal
- **`map_service.py`** — Service de génération de cartes
  - `_normalize_name()` — Normalisation noms (accents, espaces, tirets)
  - `_get_color()` — Colorisation selon passage count
  - `generate_map()` — Orchestration complète, retourne (png_bytes, rapport)
  - `save_png()` — Sauvegarde fichier PNG

### Intégrations
- **`main.py`** (modifié)
  - Appelle `map_svc.generate_map()` après Phase 5
  - Capture rapport communes non reconnues
  - Envoie PNG + statistiques en message Telegram

- **`geojson_service.py`** (corrigé)
  - Encoding UTF-8 fixé (accents français)
  - URL slugification : `Haute-Saône` → `haute-saone`

- **`nominatim_service.py`** (amélioré)
  - Priorité extraction nom: `hamlet` → `village` → `municipality`
  - Logging détaillé par point GPS

## Résultats et tests

### Test 1 : GPX simple (Territoire-de-Belfort)
- **Points GPX** : 63 (sur 1664 bruts)
- **Communes détectées** : 19 uniques
- **Communes colorisées** : 19 (100%)
- **Dépts** : 1 (90)

### Test 2 : GPX long (multi-département)
- **Points GPX** : 126 (échantillonnés)
- **Communes détectées** : 38 uniques
- **Communes colorisées** : 31 exactes + normalisées
- **Dépts** : 3 (25 Doubs, 70 Haute-Saône, 90 Territoire-de-Belfort)
- **Résultat** : Carte PNG 419 KB, bien formée

### Matching : Exact vs Normalisé
| Type | Description | Exemples |
|---|---|---|
| **Exact** | Nom commune identique | `Belfort`, `Aibre`, `Exincourt` |
| **Normalisé** | Accents/tirets différents | `Saint-Julien-lès-Montbéliard` |
| **Non-match** | Communes GeoJSON absentes du GPX | Corcelles-Ferrières, Septfontaines (normal) |

## Limitations identifiées

### 1. Nominatim vs Strava
Nominatim retourne parfois des noms de villages/hameaux différents que la liste Strava:

| Strava | Nominatim | Raison |
|---|---|---|
| HÉRICOURT | (absent) | Point GPS situé dans Lure selon Nominatim |
| SEMONDANS | (absent) | Pas dans les données Nominatim |
| ÉTOUVANS | (absent) | Situé dans Dampierre-sur-le-Doubs |
| TRÉVENANS | (absent) | Situé dans Dambenois |

**Conclusion** : Nominatim retourne les communes officielles; Strava peut inclure des lieux-dits ou des variantes. **Normal et acceptable** — le système fonctionne correctement.

### 2. Encoding UTF-8
- ✅ **Corrigé** — geojson_service.py recréé avec UTF-8 propre
- Département 70 (Haute-Saône) maintenant fonctionnel
- Accents français correctement échappés

### 3. Polices manquantes
- Avertissements matplotlib : Glyph bicyclette (🚴) et pin (📍) manquants dans la police
- **Impact** : Cosmétique uniquement, PNG généré correctement

## Statistiques de performance

| Métrique | Valeur |
|---|---|
| Temps parsing GPX | ~30 sec (1664 points → 63 échantillonnés) |
| Temps reverse geocoding | ~1 sec/point (rate limit Nominatim 1 req/sec) |
| Temps GeoJSON (cache) | ~0,5 sec |
| Temps génération PNG | ~0,5 sec |
| **Temps total** | ~2-3 minutes/GPX |
| Taille PNG moyenne | 170-420 KB (selon nombre communes) |

## Décisions prises

1. **Matching par nom normalisé** — Plus robuste que code INSEE (Nominatim ≠ GeoJSON)
2. **Priorité hamlet/village** — Plus spécifique que municipality (qui peut être la ville principale)
3. **Colorisation en 4 niveaux** — Bon compromis lisibilité vs détail
4. **Cache GeoJSON persistant** — Évite re-téléchargements
5. **Rapport d'anomalies en Telegram** — Feedback utilisateur sur communes non reconnues

## Ressources utilisées

- **Geopandas** — Manipulation GeoDataFrame depuis GeoJSON
- **Matplotlib** — Rendu PNG avec légende/statistiques
- **france-geojson** — Source GeoJSON communes par département
- **Nominatim** — Reverse geocoding GPS → communes

## Références

- [[color-communes-bot-telegram]] — Specs complètes du bot
- [[color-communes-architecture]] — Flux global du projet
- [[_index|Index Pointage_Ronfort]] — Projet parallèle avec même infra Docker

---

## Prochaines étapes

**Phase 7** : Base SQLite cumulative
- Stocker historique communes visitées (cross-GPX)
- Commandes `/cumul` et `/stats`
- Accumulation de cartes sur plusieurs uploads

**Phase 8** : Commandes avancées
- `/reset` — Réinitialiser la base
- Paramètres personnalisés (palette couleurs, taille carte)

**Phase 9** : Import historique
- 1232 sorties Strava (2012-2026)
- Accumulation cumulée depuis début

