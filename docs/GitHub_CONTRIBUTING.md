# Contributing — color-communes

Merci d'être intéressé par le projet color-communes ! 🎉

## 🚀 Comment contribuer

### 1. Forker le repo
```bash
# Sur GitHub : clic "Fork"
git clone https://github.com/yourusername/color-communes.git
cd color-communes
git remote add upstream https://github.com/Brain-Stan/color-communes.git
```

### 2. Créer une branche
```bash
git checkout -b feature/mon-feature
# ou
git checkout -b fix/mon-bug
```

### 3. Faire des changements
```bash
# Éditer fichiers
# Tester

# Committer
git add .
git commit -m "Décrire changement: quoi + pourquoi"
```

### 4. Tester avant PR
```bash
# Tests unitaires
pytest tests/ -v

# Linting
flake8 src/

# Code style
black src/

# Type checking (optionnel)
mypy src/
```

### 5. Créer Pull Request
```bash
git push origin feature/mon-feature
```
Puis créer PR sur GitHub

---

## 📋 Checklist PR

Avant de soumettre :

- [ ] **Tests passants** : `pytest tests/`
- [ ] **Code style** : `black .`
- [ ] **Linting** : `flake8`
- [ ] **Docstrings** : Toutes les fonctions documentées
- [ ] **Commit message** : Clair et descriptif
- [ ] **Pas de secrets** : Aucun token/password en clair
- [ ] **Branche à jour** : `git pull upstream main`

---

## 🎯 Domaines de contribution

### 🔴 Haute priorité
- Phase 6 : Génération PNG (geopandas)
- Phase 7 : Base SQLite (modèle, migrations)
- Tests pour phases 3-5
- Documentation déploiement

### 🟠 Moyenne priorité
- Phase 8 : Commandes `/cumul`, `/stats`
- Optimisation performance (caching, parallel processing)
- Support formats GPX supplémentaires
- UI Telegram (inline buttons, rich text)

### 🟡 Basse priorité
- Phase 9 : Import historique
- Phase 10 : Monitoring Docker
- Monitoring Nominatim API uptime
- Dashboard stats

---

## 🏗️ Architecture avant de coder

**Important** : lisez `ARCHITECTURE.md` pour comprendre :
- Flux traitement GPX
- Modules existants (phase 1-5)
- Phases restantes (6-11)
- Performance metrics

**Questions ?** → Ouvrir issue avant de coder

---

## 📝 Style de code

### Python 3.11+
```python
# Docstrings (Google style)
def parse_gpx(file_path: str) -> list[dict]:
    """Parse GPX file and return list of trackpoints.
    
    Args:
        file_path: Path to GPX file
        
    Returns:
        List of {lat, lon, ele, time} dicts
        
    Raises:
        FileNotFoundError: If file not found
        ValueError: If invalid GPX format
    """
    pass

# Type hints
def reverse_geocode(lat: float, lon: float) -> dict[str, str]:
    """Reverse geocode coordinates to commune."""
    pass

# Constants UPPERCASE
NOMINATIM_RATE_LIMIT = 1  # req/sec
DEFAULT_SAMPLE_DISTANCE = 500  # meters
```

### Commits
```
# ✅ Bon
Add Phase 6: PNG generation with geopandas

Implement map_service.py with:
- Colorize communes by visit count
- Render 1080x1080 PNG
- Add statistics overlay

Fixes #42

# ❌ Mauvais
fixed bug
WIP
asdf
```

---

## 🧪 Tests

### Ajouter un test
```python
# tests/test_my_feature.py
import pytest
from src.my_module import my_function

def test_my_function():
    """Test my_function with sample input."""
    result = my_function(input_data)
    assert result == expected_output
    
def test_my_function_error():
    """Test my_function handles errors."""
    with pytest.raises(ValueError):
        my_function(invalid_input)
```

### Fixer un test cassé
```bash
pytest tests/test_failing.py -v
# [voir erreur]
# [fixer code]
pytest tests/test_failing.py -v  # Vérifier ✅
```

---

## 🐛 Signaler un bug

1. **Vérifier** : n'existe pas déjà dans Issues
2. **Créer issue** avec :
   - Titre descriptif
   - Étapes pour reproduire
   - Output réel vs. attendu
   - Environment (OS, Python version, etc.)

**Exemple** :
```
Title: Bot timeout on large GPX files (>5000 points)

Steps:
1. Upload GPX file with 8000 trackpoints
2. Wait for processing

Expected: Carte PNG générée en < 30 sec
Actual: Timeout après 20 sec

Environment:
- Python 3.11.2
- Docker on Synology NAS
- Nominatim API public
```

---

## 💡 Feature requests

Ouvrir issue avec **[FEATURE]** prefix :

```
Title: [FEATURE] Support GeoTIFF export (Phase 8)

Description: Ajouter export en GeoTIFF pour compatibilité QGIS

Why: Intégration avec outils cartographiques profesionnels

Example: /export_geotiff → fichier GeoTIFF 500m resolution
```

---

## 📚 Ressources

- [ARCHITECTURE.md](./ARCHITECTURE.md) — Technical deep dive
- [README.md](./README.md) — Quick start
- [Issues GitHub](https://github.com/yourusername/color-communes/issues) — Bugs + features
- [Discussions GitHub](https://github.com/yourusername/color-communes/discussions) — Questions

---

## 👥 Code of Conduct

Respectez les autres contributeurs :
- Soyez courtois et constructif
- Écoutez le feedback
- Questions > criticism
- Pas de spam/self-promotion

---

## ✨ Reconnaissances

Chaque PR mergée sera documentée dans [CONTRIBUTORS.md](./CONTRIBUTORS.md).

Merci pour votre contribution ! 🙏

---

**Questions ?** → [Discussions](https://github.com/yourusername/color-communes/discussions)  
**Bugs ?** → [Issues](https://github.com/yourusername/color-communes/issues)  
**Chat** → Telegram [@yourusername](https://t.me/yourusername)
