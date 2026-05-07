---
title: "Color_communes — Phase 8 : Commandes avancées"
tags: [color-communes, phase8, history, compare, settings, gpx-list, palettes]
date: 2026-04-29
1=: informatique
2=: Python
3=: wiki technique
4=: compte-rendu
---

# Color_communes — Phase 8 : Commandes avancées

## Statut
✅ **COMPLÉTÉE** — 2026-04-29

## Objectif
Implémenter 4 commandes avancées pour analyse historique, comparaison temporelle, personnalisation et audit des fichiers traités.

## Architecture

### Nouvelles tables & champs

**Table: `user_preferences`** (nouvelles préférences utilisateur)
```sql
CREATE TABLE user_preferences (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL UNIQUE,
  color_palette TEXT DEFAULT 'classic',
  map_size TEXT DEFAULT 'medium',
  show_stats INTEGER DEFAULT 1,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: `processed_files`** (enrichie avec stats)
```sql
ALTER TABLE processed_files ADD COLUMN nb_communes INTEGER DEFAULT 0;
ALTER TABLE processed_files ADD COLUMN nb_depts INTEGER DEFAULT 0;
```

### Palettes de couleurs

4 palettes intégrées avec 4 niveaux de colorisation (1, 2-4, 5-9, 10+):

| Palette | 1 passage | 2-4 | 5-9 | 10+ |
|---------|-----------|-----|-----|-----|
| 🎨 Classique | #FFF176 | #FF8F00 | #E53935 | #B71C1C |
| 🔥 Vibrant | #FFEE58 | #FF6F00 | #D32F2F | #880E4F |
| 🌸 Pastel | #FFE082 | #FFB74D | #EF9A9A | #CE93D8 |
| ⚫ Gris | #F5F5F5 | #BDBDBD | #757575 | #212121 |

### Tailles de carte

| Taille | Résolution | Usage |
|--------|-----------|-------|
| 📱 Petit | 640×640 (8"×8") | Aperçu rapide |
| 🖥️ Moyen | 1080×1080 (12"×12") | Standard (défaut) |
| 🖨️ Grand | 1600×1600 (16"×16") | Détail haute résolution |

## Commandes implémentées

### 1. `/history YYYY-MM-DD`
**Affiche carte des communes visitées depuis une date donnée**

```
/history 2026-04-01
```

**Résultat:**
- Carte PNG montrant communes depuis 2026-04-01
- Utilise palette utilisateur (sauvegardée via /settings)
- Utilise taille utilisateur
- Caption: Date + nombre communes

**Cas d'usage:**
- Revoir sorties depuis une période
- Analyser progression cycliste
- Comparer périodes

### 2. `/compare YYYY-MM-DD`
**Affiche deux cartes côte-à-côte (avant/après)**

```
/compare 2026-04-15
```

**Résultat:**
- Deux cartes (640×480 chacune) côte-à-côte
- Gauche: communes avant 2026-04-15
- Droite: communes à partir de 2026-04-15
- Caption: Avant | Après + compte communes + "Nouvelles"

**Cas d'usage:**
- Visualiser croissance territoires
- Comparer semestraux/annuels
- Analyser évolution

### 3. `/settings`
**Menu interactif de préférences utilisateur**

```
/settings
```

**Affiche 2 rangées de boutons:**
- Palette: 🎨 Classique | 🔥 Vibrant | 🌸 Pastel | ⚫ Gris
- Taille: 📱 Petit | 🖥️ Moyen | 🖨️ Grand

**Comportement:**
- Clique → sauvegarde en `user_preferences`
- Persiste entre sessions
- `/cumul`, `/history`, `/compare` respectent préférences
- Confirmation: "✅ Palette définie: vibrant"

### 4. `/gpx_list`
**Historique simple des fichiers importés**

```
/gpx_list
```

**Résultat:**
```
📋 Historique des GPX importés

1. 2026-04-29 | sortie_jura.gpx
   🏘️ 31 communes | 📍 3 depts

2. 2026-04-28 | sortie_belfort.gpx
   🏘️ 24 communes | 📍 2 depts

3. 2026-04-25 | sortie_vosges.gpx
   🏘️ 18 communes | 📍 2 depts

... et 5 autres fichiers
```

**Cas d'usage:**
- Audit fichiers traités
- Vérifier import
- Retracer historique sorties
- Max 20 derniers affichés + compteur

## Fichiers modifiés

| Fichier | Modifications |
|---------|---------------|
| **database_service.py** | +table user_preferences, +5 méthodes (get_communes_by_date, get_communes_in_range, get_user_preference, set_user_preference, get_gpx_history) |
| **map_service.py** | +PALETTES dict (4 palettes), modified _get_color() (palette param), modified generate_map() (palette, map_size, show_stats), +generate_comparison_map() |
| **main.py** | +4 handlers (/history, /compare, /settings, /gpx_list), +2 callbacks (settings_callback, gpx_list_command), updated /help text |

## Détails implémentation

### DatabaseService Extensions

**New Methods:**
```python
def get_communes_by_date(from_date: str) → Dict
def get_communes_in_range(start_date: str, end_date: str) → Dict
def get_user_preference(user_id: int, key: str) → str
def set_user_preference(user_id: int, key: str, value: str) → bool
def get_gpx_history() → List[Dict]
def register_file(file_hash, filename, nb_communes, nb_depts) → bool
```

### MapService Enhancements

**PALETTES Dict:**
```python
PALETTES = {
    'classic': {1: '#FFF176', 2: '#FF8F00', 3: '#E53935', 4: '#B71C1C'},
    'vibrant': {1: '#FFEE58', 2: '#FF6F00', 3: '#D32F2F', 4: '#880E4F'},
    'pastel': {1: '#FFE082', 2: '#FFB74D', 3: '#EF9A9A', 4: '#CE93D8'},
    'grayscale': {1: '#F5F5F5', 2: '#BDBDBD', 3: '#757575', 4: '#212121'},
}
```

**Modified _get_color():**
- Parameter: palette (default 'classic')
- Returns color from PALETTES[palette]

**Modified generate_map():**
- Parameters: palette, map_size, show_stats
- Figsize based on map_size (small: 8×8, medium: 12×12, large: 16×16)
- Stats text conditional on show_stats flag
- Legend colors from active palette

**New generate_comparison_map():**
- 1×2 subplot layout (20×10 figsize)
- Left: communes_before
- Right: communes_after
- Single legend (lower left)
- Title: "Comparaison avant | après"

## Tests réalisés

✅ **Test 1: /history avec date valide**
- Communes depuis date affichées
- Palette utilisateur appliquée
- Caption avec date + compte communes

✅ **Test 2: /compare avec pivot date**
- Split screen avant/après généré
- Stats correctes (before count, after count, new count)
- Deux cartes visibles côte-à-côte

✅ **Test 3: /settings boutons**
- Palette buttons interactifs
- Size buttons interactifs
- Sauvegardes en DB confirmées

✅ **Test 4: Persistence préférences**
- /cumul utilise palette sauvegardée
- /history respecte map_size
- Redémarrage bot = préférences persisten

✅ **Test 5: /gpx_list historique**
- Affiche derniers 20 GPX
- Format: Date | Fichier | Communes | Depts
- Counter pour fichiers additionnels

✅ **Test 6: Gestion erreurs**
- Format date invalide → message ❌
- Aucune donnée pour période → ❌
- GeoJSON manquant → ❌

## Performance

| Métrique | Valeur |
|----------|--------|
| Temps /history (50 communes, 3 depts) | ~2-3 sec |
| Temps /compare (20+30 communes, 5 depts) | ~3-4 sec |
| Temps /settings (affichage boutons) | ~0.1 sec |
| Temps /gpx_list (lecture DB) | ~0.2 sec |
| Taille PNG small (640×640) | ~80-120 KB |
| Taille PNG medium (1080×1080) | ~170-420 KB |
| Taille PNG large (1600×1600) | ~350-800 KB |

## Améliorations futures

**Phase 9:** Import historique Strava
- 1232 sorties (2012-2026)
- Reconstruction accumulation depuis début
- Comparaison année sur année

**Phase 10:** Monitoring Docker
- Alertes Telegram erreurs
- Stats conteneur CPU/RAM
- Uptime monitoring

**Phase 11:** Tests & finitions
- QA complète
- Documentation utilisateur
- Performance optimisation

## Statistiques Phase 8

| Métrique | Valeur |
|----------|--------|
| Tables créées | 1 (user_preferences) |
| Tables modifiées | 1 (processed_files) |
| Méthodes DatabaseService | 6 |
| Handlers commandes | 4 |
| Callbacks | 2 |
| Palettes couleurs | 4 |
| Lignes code database_service.py | ~150 |
| Lignes code map_service.py | ~250 |
| Lignes code main.py | ~250 |

## Références

- [[color-communes-bot-telegram]] — Specs complètes
- [[color-communes-architecture]] — Flux global + phases
- [[color-communes-phase7]] — Base SQLite cumulative
- [[color-communes-phase6]] — Génération cartes PNG

---

## Commandes résumées

| Commande | Usage |
|----------|-------|
| `/history YYYY-MM-DD` | Communes depuis date |
| `/compare YYYY-MM-DD` | Avant/après pivot |
| `/settings` | Menu palette + taille |
| `/gpx_list` | Historique fichiers |
| `/cumul` | Carte cumulative (respecte palette) |
| `/stats` | Statistiques |
| `/reset` | Réinitialiser |

**Phase 8 Status:** ✅ COMPLÉTÉE — 4 commandes, 4 palettes, 3 tailles, persistence utilisateur
