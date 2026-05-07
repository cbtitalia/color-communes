---
title: "Color_communes — Phase 7 : Base SQLite cumulative"
tags: [color-communes, phase7, sqlite, cumul, stats, database]
date: 2026-04-29
1=: informatique
2=: Python
3=: wiki technique
4=: compte-rendu
---

# Color_communes — Phase 7 : Base SQLite cumulative

## Statut
✅ **COMPLÉTÉE** — 2026-04-29

## Objectif
Implémenter une base de données SQLite pour accumuler les communes visitées à travers plusieurs uploads GPX et fournir des commandes de consultation et réinitialisation.

## Architecture

### Schéma SQLite

**Table: `communes`** (historique cumulatif)
```sql
CREATE TABLE communes (
  id INTEGER PRIMARY KEY,
  commune TEXT NOT NULL UNIQUE,
  insee TEXT NOT NULL,
  dept TEXT NOT NULL,
  count INTEGER DEFAULT 0,
  first_visit TEXT,
  last_visit TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: `processed_files`** (détection doublons)
```sql
CREATE TABLE processed_files (
  id INTEGER PRIMARY KEY,
  file_hash TEXT NOT NULL UNIQUE,
  filename TEXT NOT NULL,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Services implémentés

**`DatabaseService`** (`database_service.py`)
- `__init__()` — initialise DB et schéma
- `upsert_communes()` — ajoute/met à jour communes après GPX
- `get_all_communes()` — récupère toutes communes pour `/cumul`
- `get_stats()` — calcule stats pour `/stats`
- `reset_database()` — réinitialise la base
- `is_file_processed()` — vérifie si GPX déjà traité (hash MD5)
- `register_file()` — enregistre GPX comme traité

### Commandes disponibles

| Commande | Résultat | Notes |
|---|---|---|
| `/cumul` | Carte PNG de toutes communes cumulées | Combine tous les GPX traités |
| `/stats` | Statistiques texte | Total communes, depts, passages, top 5 |
| `/reset` | Réinitialisation avec confirmation | Boutons inline pour confirmer |

## Flux de traitement

### GPX régulier (nouveau)
```
GPX upload
  ↓
[Phases 3-5] Parse → Geocode → GeoJSON
  ↓
Calcul hash MD5
  ↓
Vérifier si hash existe en DB
  ↓ (nouveau)
[Phase 6] Générer carte PNG + statistiques
  ↓
db_svc.register_file() — enregistrer hash
  ↓
Envoyer PNG en Telegram
```

### GPX doublons (fichier déjà traité)
```
GPX upload (même fichier)
  ↓
Calcul hash MD5
  ↓
Vérifier si hash existe en DB
  ↓ (doublons)
Message "⏭️ Fichier déjà traité"
  ↓
Suggestion: /cumul pour carte cumulative
  ↓
Arrêt (aucun traitement)
```

### Commande /cumul
```
/cumul command
  ↓
db_svc.get_all_communes()
  ↓
geojson_svc.download_geojson() pour tous depts
  ↓
map_svc.generate_map() sur données cumulées
  ↓
Envoyer PNG cumulative
```

### Commande /stats
```
/stats command
  ↓
db_svc.get_stats()
  ↓
Afficher texte: communes, depts, passages, top 5
```

### Commande /reset
```
/reset command
  ↓
Afficher boutons: "Oui" / "Non"
  ↓ (confirmation)
db_svc.reset_database() — DELETE FROM communes
  ↓
Message: "✅ Base réinitialisée"
```

## Fichiers modifiés

| Fichier | Modifications |
|---|---|
| **database_service.py** | 🆕 Créé — Service SQLite complet |
| **main.py** | Import DatabaseService, init db_svc, upsert_communes() après geocoding, 4 handlers commands (/cumul, /stats, /reset + callback), détection doublons via hash MD5 |
| **.env** | DATABASE_PATH=/data/color_communes.db (déjà présent) |

## Comportement détection doublons

**Hash MD5 du contenu GPX:**
- Calcul lors de chaque upload
- Comparaison avec `processed_files.file_hash`
- Si match → "Fichier déjà traité" + suggestion `/cumul`
- Si nouveau → traitement normal + enregistrement hash après succès

**Avantages:**
- Détecte les vrais doublons peu importe le nom du fichier
- Évite les retraitements accidentels
- Accumulation fiable en base (pas de doublons de communes)

## Tests réalisés

✅ **Test 1: Premier upload GPX**
- Traitement complet
- Communes enregistrées en DB
- Message succès avec carte + stats

✅ **Test 2: Même GPX renvoyé**
- Détection doublons fonctionnelle
- Message "⏭️ Fichier déjà traité"
- Aucun retraitement

✅ **Test 3: /cumul command**
- Combine communes de plusieurs GPX
- Affiche numéros départements
- Génère carte PNG cumulée

✅ **Test 4: /stats command**
- Affiche stats correctes
- Top communes par nombre de passages

✅ **Test 5: /reset command**
- Boutons confirmation inline
- Réinitialisation base complète

## Performance

| Métrique | Valeur |
|---|---|
| Temps upsert communes | ~0.1 sec |
| Temps /cumul (20 communes, 3 depts) | ~2-3 min (GeoJSON + map) |
| Temps /stats | ~0.2 sec |
| Temps détection doublon | ~0.01 sec |
| Taille DB (100 communes) | ~50 KB |

## Statistiques finales (Phase 7)

| Métrique | Valeur |
|---|---|
| Tables créées | 2 (communes, processed_files) |
| Méthodes DatabaseService | 7 |
| Handlers commandes | 3 (/cumul, /stats, /reset) |
| Lignes code database_service.py | ~250 |
| Lignes modifiées main.py | ~60 |

## Références

- [[color-communes-bot-telegram]] — Specs complètes
- [[color-communes-architecture]] — Flux global
- [[color-communes-phase6]] — Génération cartes PNG

---

## Prochaines étapes

**Phase 8** : Commandes avancées
- `/history` — Historique chronologique
- `/compare` — Comparer deux périodes
- Paramètres personnalisés (palette, taille)

**Phase 9** : Import historique
- 1232 sorties Strava (2012-2026)
- Reconstruction accumulation depuis début

**Phase 10** : Monitoring Docker
- Alertes Telegram sur erreurs
- Statistiques conteneur
