#!/usr/bin/env python3
"""
Génération automatique de rapports Obsidian pour issues communes
Créé quand communes non-matchées ou doublons non résolus
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

class ObsidianReporter:
    """Génère rapports .md Obsidian pour issues communes"""

    def __init__(self, output_dir: str = "/data/wiki-exports"):
        """
        Args:
            output_dir: Dossier où exporter rapports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_matching_issue(self, gpx_filename: str, commune: Dict, solution_applied: str = None) -> str:
        """
        Générer rapport issue pour commune non-matchée GeoJSON

        Args:
            gpx_filename: Nom du fichier GPX
            commune: Dict {name, postcode, dept}
            solution_applied: Solution appliquée (A/B/C/D/E) ou None

        Returns:
            Chemin fichier créé
        """

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        commune_safe = commune['name'].replace('/', '_').replace(' ', '-')
        filename = f"matching-issue_{timestamp}_{commune_safe}.md"
        filepath = self.output_dir / filename

        # Déterminer si issue est résolue
        status = "✅ Résolue" if solution_applied else "⏳ En attente"

        content = f"""---
1=: docker
2=: Synology
3=: rapport
4=: problème matching
5=: [[Problème matching communes — Issue auto-générée]]
date: {datetime.now().strftime("%Y-%m-%d")}
tags: [communes, matching, geojson, issue]
---

# Matching Issue — {gpx_filename}

> **Status**: {status}
> **Auto-généré**: {timestamp}

---

## 🔴 Problème Détecté

| Champ | Valeur |
|---|---|
| **Commune** | {commune['name']} ({commune['postcode']}) |
| **Département** | {commune['dept']} |
| **Fichier GPX** | {gpx_filename} |
| **Issue Type** | Non colorisée sur carte (GeoJSON mismatch) |
| **Status** | {status} |

---

## 📋 Context

Commune extraite du GPX mais:
- ❌ Ne match pas avec GeoJSON du département
- ⚠️ Non colorisée sur la carte Color_communes
- 📍 Localisation: {commune['dept']} / {commune['name']}

---

## 💡 Solutions Proposées

### Solution A : Ajouter dans GeoJSON

**Description:** La commune existe mais manque du fichier GeoJSON

**Action :** Ajouter "{commune['name']}" au GeoJSON du département {commune['dept']}

**Impact:**
- ✅ Commune sera colorisée
- ✅ Match automatique futur
- ❌ Modification GeoJSON (source externe)

**Status:** {'✅ APPLIQUÉE' if solution_applied == 'A' else '☐ À faire'}

---

### Solution B : Corriger Code Postal

**Description:** Code postal incorrect → mismatch avec GeoJSON

**Actuel :** {commune['postcode']}
**Correct :** [À déterminer]

**Action :** Mettre à jour dans base de données

```sql
UPDATE communes
SET postcode = '[CODE_CORRECT]'
WHERE name = '{commune['name']}' AND dept = '{commune['dept']}'
```

**Impact:**
- ✅ Match automatique
- ✅ Commune colorisée
- ✅ Impact faible (1 commune)

**Status:** {'✅ APPLIQUÉE' if solution_applied == 'B' else '☐ À faire'}

---

### Solution C : Normaliser Nom

**Description:** Variante nom (accent/tiret/espace différent)

**Variantes possibles :**
- {commune['name']}-le-...
- {commune['name']}'...
- Saint-{commune['name']}
- [Autre :]

**Action :** Ajouter règle normalisation dans code

**Impact:**
- ✅ Futur automatique
- ✅ Pas de modification GeoJSON
- ✅ Réutilisable

**Status:** {'✅ APPLIQUÉE' if solution_applied == 'C' else '☐ À faire'}

---

### Solution D : Marquer "No Match"

**Description:** Accepter que commune ne match pas

**Raison :**
- ☐ Commune n'existe pas
- ☐ Erreur OCR/extraction
- ☐ Code postal invalide
- ☐ [Autre :]

**Action :** Marquer dans DB

```sql
UPDATE communes
SET is_invalid = 1, notes = 'No match acceptable'
WHERE name = '{commune['name']}' AND dept = '{commune['dept']}'
```

**Impact:**
- ✅ Pas de faux positifs
- ❌ Commune perdue (non colorisée)

**Status:** {'✅ APPLIQUÉE' if solution_applied == 'D' else '☐ À faire'}

---

### Solution E : Investigation Manuelle

**Description:** Enquête approfondie requise

**À faire :**
- [ ] Vérifier si commune existe dans GeoJSON
- [ ] Chercher variantes dans OSM/Nominatim
- [ ] Vérifier coordonnées GPS du GPX
- [ ] Contacter data source

**Status:** ☐ À investiguer

---

## ✅ Résolution

### Choix Approuvé

**Solution choisie :** {solution_applied if solution_applied else '[À déterminer]'}

**Raison :** [À compléter]

**Détails :** [Si code postal / nom : indiquer la valeur]

---

### Signature

**Approuvé par :** [Utilisateur]
**Date :** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Notes :** [Optionnel]

---

## 🔗 Références

- [[strategie-apprentissage-communes]] — Stratégie globale
- [[communes-validation-FORM]] — Formulaire validation
- [[matching-issue-TEMPLATE]] — Template original

---

**Status:** {status}
**Créé par:** Color_communes Bot
**Action requise :** {'Aucune (résolu)' if solution_applied else 'Validation utilisateur'}
"""

        # Écrire fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"✅ Issue Obsidian créée: {filename}")
        return str(filepath)

    def generate_validation_summary(self, gpx_filename: str, communes_before: List[Dict], communes_after: List[Dict], corrections: List[Dict]) -> str:
        """
        Générer résumé validation GPX

        Args:
            gpx_filename: Nom GPX
            communes_before: Communes avant corrections
            communes_after: Communes après corrections
            corrections: Liste corrections appliquées

        Returns:
            Chemin fichier créé
        """

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"validation-summary_{timestamp}_{gpx_filename.replace('/', '_')}.md"
        filepath = self.output_dir / filename

        # Analyser corrections
        duplicates_removed = len([c for c in corrections if c['type'] == 'duplicate_resolved'])
        depts_resolved = len([c for c in corrections if c['type'] == 'multi_dept'])
        geojson_resolved = len([c for c in corrections if c['type'] == 'geojson_matching'])

        content = f"""---
1=: docker
2=: Synology
3=: rapport
4=: validation
5=: [[Résumé validation communes pour {gpx_filename}]]
date: {datetime.now().strftime("%Y-%m-%d")}
tags: [communes, validation, summary]
---

# Résumé Validation — {gpx_filename}

> **Date:** {timestamp}
> **Status:** ✅ Validation complétée

---

## 📊 Statistiques

| Métrique | Avant | Après | Changement |
|---|---|---|---|
| **Communes** | {len(communes_before)} | {len(communes_after)} | -{len(communes_before)-len(communes_after)} |
| **Doublons supprimés** | — | — | {duplicates_removed} |
| **Depts résolus** | — | — | {depts_resolved} |
| **GeoJSON résolus** | — | — | {geojson_resolved} |
| **Corrections totales** | — | — | {len(corrections)} |

---

## ✅ Corrections Appliquées

"""

        # Détailler corrections
        for i, correction in enumerate(corrections, 1):
            content += f"\n### {i}. {correction.get('type', 'Unknown')}\n\n"
            content += f"- **Commune :** {correction.get('commune')}\n"

            if correction['type'] == 'duplicate_resolved':
                content += f"- **Action :** Garder code postal {correction.get('chosen_postcode')}\n"
            elif correction['type'] == 'duplicate_ignored':
                content += f"- **Action :** Ignoré (les deux versions)\n"
            elif correction['type'] == 'multi_dept':
                content += f"- **Action :** Dept {correction.get('chosen_dept')}\n"
            elif correction['type'] == 'geojson_matching':
                content += f"- **Solution :** {correction.get('solution')}\n"
                if correction.get('detail'):
                    content += f"- **Détail :** {correction['detail']}\n"

            content += "\n"

        content += f"""
---

## 📋 Communes Avant / Après

### Supprimées ({len(communes_before)-len(communes_after)})

"""

        removed = [c for c in communes_before if c['name'] not in [a['name'] for a in communes_after]]
        for comm in removed:
            content += f"- ❌ {comm['name']} ({comm['postcode']})\n"

        content += f"""
### Conservées ({len(communes_after)})

"""

        for comm in sorted(communes_after, key=lambda x: x.get('dept', ''))[:10]:
            content += f"- ✅ {comm['name']} ({comm['postcode']}) — Dept {comm.get('dept')}\n"

        if len(communes_after) > 10:
            content += f"\n... et {len(communes_after)-10} autres\n"

        content += f"""
---

## 🔗 Références

- GPX traité : {gpx_filename}
- Cartes générées :
  - Avant : {gpx_filename}_original.png
  - Après : {gpx_filename}_corrected.png
  - Comparaison : {gpx_filename}_comparison.png

---

**Status:** ✅ Validation terminée
**Créé par:** Color_communes Learning Bot
"""

        # Écrire fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"✅ Résumé validation créé: {filename}")
        return str(filepath)

    def generate_batch_report(self, gpx_files: List[str]) -> str:
        """
        Générer rapport batch : plusieurs GPX validés

        Args:
            gpx_files: Liste fichiers GPX validés

        Returns:
            Chemin fichier créé
        """

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"batch-validation-report_{timestamp}.md"
        filepath = self.output_dir / filename

        content = f"""---
1=: docker
2=: Synology
3=: rapport
4=: batch
5=: [[Rapport batch validation communes]]
date: {datetime.now().strftime("%Y-%m-%d")}
tags: [communes, validation, batch]
---

# Rapport Batch Validation

> **Date:** {timestamp}
> **Fichiers traités:** {len(gpx_files)}

---

## 📊 Résumé

| GPX | Communes | Corrections | Status |
|---|---|---|---|
"""

        for gpx in gpx_files:
            content += f"| {gpx} | — | — | ✅ |\n"

        content += f"""
---

## 📝 Prochaines étapes

- [ ] Vérifier rapports individuels
- [ ] Valider corrections appliquées
- [ ] Générer nouvelles cartes
- [ ] Archiver résultats

---

**Status:** ✅ Batch terminé
**Créé par:** Color_communes Learning Bot
"""

        # Écrire fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"✅ Rapport batch créé: {filename}")
        return str(filepath)
