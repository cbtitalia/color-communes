# IMPLÉMENTATION AUTO-ENRICHISSEMENT COMMUNES
**Date:** 2026-05-02  
**Statut:** Guide d'activation  
**Objectif:** Auto-ajouter communes du 90/70/25/39/68/88 progressivement

---

## 📊 SITUATION ACTUELLE

### État du code
- ✅ `main.py` : traite communes via `CommuneProcessor`
- ✅ `commune_processor.py` : valide/corrige communes
- ✅ `communes_mapping.csv` : 16 communes mappées actuellement
- ✅ Lookup files : 2,613 communes (6 départements) prêts

### Flux de traitement (phases)
```
GPX → Phase 1: Parse GPX
    → Phase 2: Reverse geocoding (Nominatim)
    → Phase 3: Cache GeoJSON
    → Phase 4: Colorisation map
    → Phase 4.5: commune_processor (correction/validation)
    → Phase 5: Génération carte PNG
```

---

## 🔧 MODIFICATION CODE NÉCESSAIRE

### Approche recommandée: Enrichir CommuneProcessor

**Objectif:** Quand une commune UNKNOWN est trouvée, chercher dans les lookup files

**Fichiers à modifier:**
1. `/app/commune_processor.py` (en conteneur Docker)
2. Ajouter loading des lookup files au démarrage
3. Ajouter logique auto-add à communes_mapping.csv

**Pseudo-code:**

```python
class CommuneProcessor:
    def __init__(self, mapping_file):
        self.mapping = load_csv(mapping_file)  # communes_mapping.csv
        
        # 🆕 NOUVEAU : Charger tous les lookup files
        self.lookups = {
            '25': load_csv('/app/communes_25_lookup.csv'),
            '39': load_csv('/app/communes_39_lookup.csv'),
            '68': load_csv('/app/communes_68_lookup.csv'),
            '70': load_csv('/app/communes_70_lookup.csv'),
            '88': load_csv('/app/communes_88_lookup.csv'),
            '90': load_csv('/app/communes_90_lookup.csv'),
        }
    
    def process(self, commune_name):
        # Chercher dans mapping actuel
        if commune_name in self.mapping:
            return ProcessStatus.VALID
        
        # 🆕 NOUVEAU : Chercher dans tous les lookup files
        for dept_code, lookup in self.lookups.items():
            if commune_name in lookup:
                # Auto-ajouter à communes_mapping.csv
                self.add_to_mapping(commune_name, lookup[commune_name])
                logger.info(f"✅ Auto-ajoutée depuis lookup {dept_code}: {commune_name}")
                return ProcessStatus.VALID
        
        # Fallback : UNKNOWN (acceptée par Nominatim)
        return ProcessStatus.UNKNOWN
    
    def add_to_mapping(self, commune_name, data):
        """Ajouter commune à communes_mapping.csv"""
        with open(self.mapping_file, 'a') as f:
            f.write(f"{commune_name},{data['nom_correct']},{data['code_insee']},...\n")
```

---

## 🐳 CONFIGURATION DOCKER

### 1. Mise à jour docker-compose.yml

Ajouter volumes pour les lookup files:

```yaml
services:
  color-communes:
    volumes:
      - /volume1/docker/color-communes/data:/data
      - /volume1/docker/color-communes/communes_mapping.csv:/app/communes_mapping.csv
      
      # 🆕 NOUVEAU : Lookup files
      - /volume1/docker/color-communes/communes_25_lookup.csv:/app/communes_25_lookup.csv
      - /volume1/docker/color-communes/communes_39_lookup.csv:/app/communes_39_lookup.csv
      - /volume1/docker/color-communes/communes_68_lookup.csv:/app/communes_68_lookup.csv
      - /volume1/docker/color-communes/communes_70_lookup.csv:/app/communes_70_lookup.csv
      - /volume1/docker/color-communes/communes_88_lookup.csv:/app/communes_88_lookup.csv
      - /volume1/docker/color-communes/communes_90_lookup.csv:/app/communes_90_lookup.csv
```

### 2. Copier les lookup files sur Synology

**Depuis Windows:**
1. Ouvrir Synology DSM (http://synology.local:5000)
2. Aller dans File Station
3. Naviguer vers `/volume1/docker/color-communes/`
4. Uploader les fichiers:
   - communes_25_lookup.csv
   - communes_39_lookup.csv
   - communes_68_lookup.csv
   - communes_70_lookup.csv
   - communes_88_lookup.csv
   - communes_90_lookup.csv

**Ou via SSH (si activé):**
```bash
scp communes_*_lookup.csv admin@synology.local:/volume1/docker/color-communes/
```

### 3. Redémarrer Docker

Dans Synology DSM:
1. Container Manager → Container
2. Chercher "color_communes_bot"
3. Cliquer droit → Restart

**OU via SSH:**
```bash
docker-compose -f /volume1/docker/color-communes/config/docker-compose.yml down
docker-compose -f /volume1/docker/color-communes/config/docker-compose.yml up -d
```

---

## ✅ TEST & VALIDATION

### Test avec GPX réel: 2026_01_90_70_25.gpx

**Résultats attendus:**
```
Communes détectées: 83 total
  ✅ Mappées actuelles: 4 (Belfort, Moval, Offemont, Valdoie)
  🆕 Auto-ajoutées: 79 (depuis lookup files)
```

**Communes qui vont être ajoutées:**

**Dept 90 (18 nouvelles):**
Andelnans, Argiésans, Banvillars, Bavilliers, Bermont, Botans, Bourogne, Buc, Châtenois-les-Forges, Cravanche, Danjoutin, Dorans, Essert, Évette-Salbert, Pérouse, Sevenans, Trévenans, Urcerey

**Dept 70 (18 nouvelles):**
Brevilliers, Chagey, Châlonvillars, Champey, Chenebier, Coisevaux, Couthenans, Échavanne, Échenans-sous-Mont-Vaudois, Étobon, Frahier-et-Chatebier, Héricourt, Luze, Mandrevillars, Tavey, Trémoins, Verlans, Vyans-le-Val

**Dept 25 (43 nouvelles):**
Aibre, Allenjoie, Allondans, Arbouans, Audincourt, Bart, Bavans, Berche, Bethoncourt, Brognard, Colombier-Fontaine, Courcelles-lès-Montbéliard, Dambenois, Dampierre-sur-le-Doubs, Dasle, Désandans, Dung, Échenans, Étouvans, Étupes, Exincourt, Fesches-le-Châtel, Grand-Charmont, Issans, Laire, Lougres, Mathay, Montbéliard, Nommay, Présentevillers, Raynans, Saint-Julien-lès-Montbéliard, Sainte-Marie, Sainte-Suzanne, Seloncourt, Semondans, Sochaux, Taillecourt, Valentigney, Vandoncourt, Vernoy, Vieux-Charmont, Voujeaucourt

### Vérification après test:
```bash
# Via DSM File Station:
# Vérifier communes_mapping.csv
# Taille devrait passer de ~1KB à ~5-10KB (79 lignes ajoutées)

# Via logs Docker:
docker logs color_communes_bot | grep "Auto-ajoutée"
# Devrait afficher: ✅ Auto-ajoutée depuis lookup 90: Andelnans
#                   ✅ Auto-ajoutée depuis lookup 90: Argiésans
#                   ... etc
```

---

## 📋 CHECKLIST D'ACTIVATION

- [ ] 1. Vérifier lookup files créés (6 fichiers CSV)
- [ ] 2. Modifier `commune_processor.py` pour loading lookup
- [ ] 3. Copier lookup files sur Synology NAS
- [ ] 4. Mettre à jour `docker-compose.yml` (volumes)
- [ ] 5. Redémarrer Docker container
- [ ] 6. Vérifier logs Docker (pas d'erreurs)
- [ ] 7. Importer GPX test via Telegram
- [ ] 8. Vérifier communes_mapping.csv s'enrichit
- [ ] 9. Vérifier carte PNG affiche 79+ communes
- [ ] 10. Monitor futur enrichissement

---

## 🚀 OPTIMISATIONS FUTURES

1. **Cache des lookup files en mémoire** (perf)
2. **Statistiques auto-enrichissement** (combien ajoutées par semaine)
3. **Contrôle qualité** (valider INSEE avant auto-add)
4. **Interface web** (voir communes_mapping en temps réel)
5. **Export cumulative** (toutes communes jamais traversées)

---

## 📞 SUPPORT

- **Logs:** Voir Docker → Container logs
- **Fichiers:** Synology DSM → File Station → /volume1/docker/color-communes/
- **Git:** Vérifier commits pour tracer modifications

**Dernière mise à jour:** 2026-05-02
