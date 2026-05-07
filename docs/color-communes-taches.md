---
title: "Color_communes — Tâches & temps estimatifs"
tags: [android, flutter, strava, cartographie, taches, proj1-color]
date: 2026-04-24
type: checklist
statut: actif
1=: velo
2=: Strava
3=: doc projet
4=: checklist
---

- REF
  - 1= theme:: [[1=velo]] [[1=cartographie]] [[1=android]]
  - 2= marque:: [[2=Strava]]
  - 3= systeme:: [[3=doc projet]]
  - 4= type:: [[4=checklist]]

# Color_communes — Tâches & temps estimatifs

> Liste complète des tâches pour développer l'app Android Color_communes.
> Architecture complète : [[color-communes-definition]]

---

## Récapitulatif

| Phase | Tâches | Temps estimé |
|---|---|---|
| 1 — Environnement & structure | 5 tâches | ~2h00 |
| 2 — Connexion Strava | 4 tâches | ~3h00 |
| 3 — Traitement communes | 5 tâches | ~4h00 |
| 4 — Base de données cumulative | 4 tâches | ~3h00 |
| 5 — GeoJSON & Garmin | 3 tâches | ~2h00 |
| 6 — Génération image | 4 tâches | ~4h00 |
| 7 — Partage social | 3 tâches | ~2h00 |
| 8 — Import historique Synology | 3 tâches | ~3h00 |
| 9 — Tests & finitions | 4 tâches | ~3h00 |
| **Total** | **35 tâches** | **~26h00** |

---

## Phase 1 — Environnement & structure Flutter (≈ 2h00)

- [ ] Installer Flutter SDK + Android Studio `30 min`
- [ ] Créer le projet Flutter `color_communes` `10 min`
- [ ] Ajouter les dépendances dans `pubspec.yaml` `15 min`
      ```yaml
      dependencies:
        sqflite: ^2.3.0        # SQLite local
        http: ^1.2.0           # Requêtes API
        share_plus: ^9.0.0     # Partage Android
        flutter_secure_storage # Tokens OAuth
        cached_network_image   # Cache images
      ```
- [ ] Créer la structure des dossiers (lib/screens, lib/services, lib/models, lib/db) `15 min`
- [ ] Configurer le thème et l'icône de l'app `30 min`

**Durée Phase 1 : ~2h00**

---

## Phase 2 — Connexion Strava OAuth2 (≈ 3h00)

- [ ] Créer une app sur [strava.com/settings/api](https://www.strava.com/settings/api) et noter Client ID + Secret `15 min`
- [ ] Implémenter le flux OAuth2 (WebView → code → token) `1h30`
      → Redirect URI : `color-communes://oauth`
      → Scopes : `activity:read_all`
- [ ] Stocker le token de façon sécurisée (`flutter_secure_storage`) `30 min`
- [ ] Implémenter le refresh automatique du token (expire après 6h) `45 min`

**Durée Phase 2 : ~3h00**

---

## Phase 3 — Traitement des communes (≈ 4h00)

- [ ] Service `StravaService` : récupérer la liste des activités avec pagination `1h00`
      ```dart
      GET https://www.strava.com/api/v3/athlete/activities
        ?per_page=50&page=1&after=timestamp
      ```
- [ ] Service `StravaService` : récupérer le stream GPS d'une activité `30 min`
      ```dart
      GET https://www.strava.com/api/v3/activities/{id}/streams
        ?keys=latlng&key_by_type=true
      ```
- [ ] Service `NominatimService` : reverse geocoding par point GPS `1h00`
      ```dart
      GET https://nominatim.openstreetmap.org/reverse
        ?lat=&lon=&format=json&addressdetails=1
      ```
      → Extraire `address.postcode` et `address.municipality`
- [ ] Optimiser : ne geocoder que 1 point tous les **200m** (au lieu de 500m pour meilleure précision — voir [[color-communes-phase3-200m-analysis]]) `30 min`
- [ ] Respecter le rate limit Nominatim (1 requête/seconde max) `30 min`

**Durée Phase 3 : ~4h00**

---

## Phase 4 — Base de données cumulative SQLite (≈ 3h00)

- [ ] Créer le schéma SQLite (tables `communes`, `activites`, `geojson_cache`) `30 min`
- [ ] Service `DatabaseService` : CRUD communes + activités `1h00`
      → Insérer nouvelle commune / incrémenter `nb_passages` si existante
- [ ] Logique de déduplication : ne pas retraiter une activité déjà en base `30 min`
      → Vérifier `strava_id` dans la table `activites`
- [ ] Ecran "Statistiques" : total communes, départements, sorties, première visite `1h00`

**Durée Phase 4 : ~3h00**

---

## Phase 5 — GeoJSON communes & export Garmin (≈ 2h00)

- [ ] Service `GeoJsonService` : télécharger le GeoJSON d'un département depuis france-geojson.gregoiredavid.fr et le mettre en cache SQLite `45 min`
      ```
      GET https://france-geojson.gregoiredavid.fr/repo/departements/
          {num}-{nom}/communes-{num}-{nom}.geojson
      ```
- [ ] Générer le GeoJSON colorisé final (communes visitées = colorisées) `45 min`
      → Couleur par fréquence : 1 passage = `#FFF176`, 5+ = `#E53935`
- [ ] Export fichier `.geojson` dans le stockage Android + intent de partage vers Garmin/PC `30 min`

**Durée Phase 5 : ~2h00**

---

## Phase 6 — Génération de l'image partageable (≈ 4h00)

- [ ] Configurer un compte Mapbox et récupérer le token API `15 min`
- [ ] Service `MapboxService` : envoyer le GeoJSON → recevoir PNG `1h30`
      ```
      GET https://api.mapbox.com/styles/v1/mapbox/light-v11/static/
          geojson({...})/auto/1080x1080@2x
          ?access_token=TOKEN
      ```
- [ ] Overlay statistiques sur l'image (Canvas Flutter) `1h30`
      ```
      🚴 {nb_sorties} sorties  |  {nb_communes} communes  |  {nb_depts} départements
      Depuis {annee_debut} — dernière sortie : {date}
      ```
- [ ] Sélecteur de format : Instagram carré, portrait, Facebook, Stories `45 min`

**Durée Phase 6 : ~4h00**

---

## Phase 7 — Partage social (≈ 2h00)

- [ ] Intégrer `share_plus` : partage image PNG vers toutes les apps Android `45 min`
- [ ] Générer automatiquement un texte de partage avec hashtags `45 min`
      ```
      🗺️ {nb_communes} communes traversées | {nb_sorties} sorties depuis {annee}
      #velo #cycling #strava #cartographie
      ```
- [ ] Ecran de prévisualisation avant partage (choix format + édition légende) `30 min`

**Durée Phase 7 : ~2h00**

---

## Phase 8 — Import historique depuis Synology (≈ 3h00)

- [ ] Script Python sur Synology : générer `communes_historique.json` depuis les 1 232 sorties existantes `1h30`
      → Utilise le pipeline [[colorisation-communes-garmin]] existant
      → Format : `[{id_insee, nom, dept, date_1ere_visite, nb_passages, derniere_visite}]`
- [ ] Ecran "Import" dans l'app : charger le fichier JSON depuis le stockage Android `45 min`
- [ ] Peupler la base SQLite depuis le JSON importé + valider les données `45 min`

**Durée Phase 8 : ~3h00**

---

## Phase 9 — Tests & finitions (≈ 3h00)

- [ ] Test complet : nouvelle sortie Strava → détection → communes ajoutées → image générée `1h00`
- [ ] Gestion hors ligne : app fonctionnelle sans internet (données en cache) `30 min`
- [ ] Gestion des erreurs : rate limit Nominatim, Strava API down, GeoJSON indisponible `1h00`
- [ ] Optimisation batterie : traitement en background service (WorkManager) `30 min`

**Durée Phase 9 : ~3h00**

---

## Ordre recommandé

```
Semaine 1 (~8h)
  Phase 1 — Flutter setup
  Phase 2 — Strava OAuth
  Phase 3 — Traitement communes (début)

Semaine 2 (~8h)
  Phase 3 — Traitement communes (fin)
  Phase 4 — Base SQLite cumulative
  Phase 5 — GeoJSON & Garmin

Semaine 3 (~8h)
  Phase 6 — Génération image Mapbox
  Phase 7 — Partage social

Semaine 4 (~5h)
  Phase 8 — Import historique Synology
  Phase 9 — Tests & finitions
```

---

## Dépendances entre phases

```
Phase 1 (Flutter)
    └→ Phase 2 (Strava OAuth)
        └→ Phase 3 (Traitement communes)
            └→ Phase 4 (SQLite)
                ├→ Phase 5 (GeoJSON + Garmin)
                └→ Phase 6 (Image)
                    └→ Phase 7 (Partage)
Phase 8 (Import) → indépendant, peut se faire en parallèle de Phase 4
Phase 9 (Tests) → après toutes les phases
```

---

## Références

- [[color-communes-definition]] — Architecture complète
- [[colorisation-communes-garmin]] — Pipeline Python existant (base algorithmique)
- [[_index|Index Color_communes]]
