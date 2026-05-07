# color-communes

Telegram bot qui transforme vos fichiers GPX en cartes colorées des communes françaises visitées à vélo.

**[Demo](#demo) • [Installation](#installation) • [Architecture](#architecture) • [Phases](#phases) • [Contributing](#contributing)**

---

## 🚀 Démarrage rapide

### Prérequis
- Docker + Docker Compose
- Token Telegram ([@BotFather](https://t.me/botfather))
- Python 3.11+

### Installation 5 min

```bash
git clone https://github.com/cbtitalia/color-communes.git
cd color-communes

# Créer .env
cp .env.example .env
# Éditer : TELEGRAM_BOT_TOKEN, CHAT_ID

# Déployer
docker-compose up -d

# Tester
curl http://localhost:8080/health
```

---

## 📋 Fonctionnement

1. **Envoyez un fichier GPX** via Telegram
2. **Bot traite** : parsing points GPS + reverse geocoding
3. **Reçoit une carte PNG** : communes colorées par nb passages

### Formats supportés
- ✅ Garmin
- ✅ Strava
- ✅ Komoot

---

## 🏗️ Architecture

[Voir ARCHITECTURE.md](./ARCHITECTURE.md) pour détails techniques.

### Phases de développement

| Phase | Statut | Tâche |
|---|---|---|
| 1-5 | ✅ | Setup, parsing, geocoding |
| **6** | **⏳** | **Génération PNG** |
| 7-11 | 📋 | SQLite, commandes, tests |

---

## 🔐 Licence

MIT — Voir [LICENSE](./LICENSE)

---

## 🤝 Contributing

Voir [CONTRIBUTING.md](./CONTRIBUTING.md)

---

**Code source complet** : `/volume1/docker/color-communes/` sur Synology NAS
