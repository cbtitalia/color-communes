---
title: "Color_communes — Définition & architecture"
tags: [android, strava, gpx, cartographie, social, projet, proj1-color]
date: 2026-04-24
type: note
statut: définition
1=: velo
2=: Strava
3=: doc projet
4=: note documentaire
---

- REF
  - 1= theme:: [[1=velo]] [[1=cartographie]] [[1=android]]
  - 2= marque:: [[2=Strava]]
  - 3= systeme:: [[3=doc projet]]
  - 4= type:: [[4=note documentaire]]

# Color_communes — Définition & architecture

> Application Android personnelle qui construit une carte cumulative des communes traversées à vélo, s'alimentant à chaque nouvelle trace GPX, et génère une image partageable sur Facebook/Instagram.
> Projet : [[_index|Color_communes]]

---

## Concept

**Idée centrale** : chaque sortie vélo enrichit une carte vivante. Avec le temps, la carte raconte l'histoire complète de tous les territoires parcourus. L'image générée est partageable sur les réseaux sociaux.

```
1 232 sorties Strava (2012→2026)
    + chaque nouvelle sortie
    ↓
Carte cumulative des communes visitées
    ↓
Image stylisée (Instagram, Facebook)
    ↓
Partage en 1 tap
```

---

## Fonctionnalités

### Core
- Connexion Strava OAuth2
- Récupération automatique des nouvelles activités
- Identification des communes traversées (Nominatim API)
- Base de données locale SQLite cumulative
- Téléchargement GeoJSON communes depuis [france-geojson.gregoiredavid.fr](https://france-geojson.gregoiredavid.fr) (par département, mis en cache)
- Export GeoJSON colorisé → Garmin

### Génération d'image
- Rendu carte stylisé (Mapbox Static API ou rendu WebView)
- Formats : carré 1080×1080 (Instagram), paysage 1200×630 (Facebook)
- Overlay statistiques personnalisable

### Partage social
- Partage natif Android → Facebook, Instagram, WhatsApp, etc.
- Légende automatique générée

### Historique
- Filtrage par période (cette année, toujours, personnalisé)
- Colorisation par fréquence (1 passage = clair, souvent = foncé)
- Statistique "première fois" sur une commune

---

## Modèle de données (SQLite Android)

### Table `communes`

| Colonne | Type | Description |
|---|---|---|
| id_insee | TEXT PK | Code INSEE commune |
| nom | TEXT | Nom de la commune |
| departement | TEXT | Numéro département |
| date_1ere_visite | DATE | Première sortie dans cette commune |
| nb_passages | INT | Nombre de sorties passant par là |
| derniere_visite | DATE | Date de la dernière sortie |

### Table `activites`

| Colonne | Type | Description |
|---|---|---|
| strava_id | TEXT PK | ID activité Strava |
| date | DATE | Date de la sortie |
| nom | TEXT | Nom de l'activité |
| communes_ids | TEXT | JSON array des codes INSEE |
| traite | BOOL | True si déjà intégré |

### Table `geojson_cache`

| Colonne | Type | Description |
|---|---|---|
| departement | TEXT PK | Numéro département |
| geojson | TEXT | Contenu GeoJSON complet |
| date_telechargement | DATE | Pour invalidation cache |

---

## Architecture technique

```
┌─────────────────────────────────────────────────────┐
│                  App Android (Flutter)               │
│                                                     │
│  ┌──────────────┐    ┌───────────────────────────┐  │
│  │ Strava OAuth │    │  SQLite (communes, traces) │  │
│  └──────┬───────┘    └──────────────┬────────────┘  │
│         │                           │               │
│  ┌──────▼──────────────────────────▼────────────┐  │
│  │              Core Engine                      │  │
│  │  - Fetch activités Strava                    │  │
│  │  - Reverse geocoding (Nominatim)             │  │
│  │  - Mise à jour base communes                 │  │
│  │  - Génération GeoJSON colorisé               │  │
│  └──────────────────┬───────────────────────────┘  │
│                     │                               │
│  ┌──────────────────▼───────────────────────────┐  │
│  │           Rendu & Partage                     │  │
│  │  - Mapbox Static API → image PNG             │  │
│  │  - Overlay stats (Canvas Android)            │  │
│  │  - Android Share Intent                      │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

APIs externes :
  - api.strava.com (activités + streams GPS)
  - nominatim.openstreetmap.org (reverse geocoding)
  - france-geojson.gregoiredavid.fr (GeoJSON communes)
  - api.mapbox.com (rendu image statique)
```

---

## Génération de l'image partageable

### Rendu via Mapbox Static Images API

> [!warning] Ne jamais écrire le token Mapbox en dur dans le code Flutter.
> Utiliser `flutter_dotenv` + fichier `.env` exclu du dépôt Git (`.gitignore`).

```dart
// Charger depuis .env au démarrage de l'app
await dotenv.load(fileName: ".env");
final mapboxToken = dotenv.env['MAPBOX_TOKEN']!;
```

```
POST https://api.mapbox.com/styles/v1/mapbox/light-v11/static/
  geojson({features: [communes_colorisées]})
  /auto/1080x1080@2x
  ?access_token=$mapboxToken
```

→ Retourne une image PNG prête à partager.

**Tarif** : gratuit jusqu'à 200 000 requêtes/mois (très largement suffisant).

### Overlay statistiques (Canvas Android)

Texte superposé sur l'image :

```
🚴 1 232 sorties  |  287 communes  |  12 départements
Depuis 2012 — dernière sortie : 20 avril 2026
```

### Formats de sortie

| Réseau | Format | Résolution |
|---|---|---|
| Instagram carré | 1:1 | 1080×1080 |
| Instagram portrait | 4:5 | 1080×1350 |
| Facebook | 1.91:1 | 1200×630 |
| Stories | 9:16 | 1080×1920 |

---

## Initialisation (import historique)

Le script Python existant sur Synology traite les 1 232 sorties → génère un fichier d'export `communes_historique.json` → importé dans l'app au premier lancement.

```json
[
  {"id_insee": "90010", "nom": "Bavilliers", "dept": "90",
   "date_1ere_visite": "2019-06-15", "nb_passages": 7,
   "derniere_visite": "2026-04-20"},
  ...
]
```

---

## Stack technique recommandée

| Composant | Technologie | Raison |
|---|---|---|
| App Android | Flutter (Dart) | Multiplateforme, rapide à développer |
| Base locale | SQLite chiffré (sqflite + sqlcipher) | Données GPS personnelles protégées |
| Secrets app | flutter_dotenv | Tokens hors du code source |
| Strava API | http + OAuth2 | Bibliothèques Flutter disponibles |
| Geocoding | Nominatim (REST) | Gratuit, pas de clé API |
| GeoJSON communes | france-geojson.gregoiredavid.fr | Téléchargement à la demande |
| Rendu image | Mapbox Static API | Simple, résultat pro |
| Partage | Share_plus (Flutter) | Intent natif Android/iOS |

**Règles sécurité Flutter :**
- `.env` à la racine du projet → listé dans `.gitignore`
- Client Secret Strava → jamais dans le code → `.env` uniquement
- Token Mapbox → `.env` uniquement
- SQLite chiffré avec `sqlcipher_flutter_libs` (clé dérivée de l'identifiant Android)
- Tokens OAuth Strava stockés dans `flutter_secure_storage` (Keystore Android)

---

## Ce que ça donne sur Instagram

```
📍 Ma carte vélo 2026

🗺️ 287 communes traversées
🚴 1 232 sorties depuis 2012
📍 12 départements explorés
🏆 Dernière découverte : Delle (90100) — 20 avril 2026

[Image : carte Alsace-Franche-Comté avec communes colorisées]

#velo #cycling #strava #cartographie #belfort #alsace
```

---

## Références

- [[colorisation-communes-garmin]] — Pipeline Python actuel (base algorithmique)
- [[Velo/Strava/strava-stats-historique]] — Export API Strava existant
- [[_index|Index Color_communes]]
