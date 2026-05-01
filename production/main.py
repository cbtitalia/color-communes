#!/usr/bin/env python3
import os
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from difflib import get_close_matches
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from gpx_parser import GpxParser
from nominatim_service import NominatimService
from geojson_service import GeoJsonService
from map_service import MapService
from database_service import DatabaseService
from learning_service import LearningService
from validation_handler import ValidationHandler
from obsidian_reporter import ObsidianReporter
from commune_processor import CommuneProcessor, ProcessStatus
from import_communes import CommunesImporter
from color_communes_auto_enrich import ensure_communes_enriched

# Charger .env
env_file = Path("/data/.env") if Path("/data/.env").exists() else Path(".env")
load_dotenv(env_file)

# Config logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_USER_ID = int(os.getenv('TELEGRAM_USER_ID', 0))
NOMINATIM_EMAIL = os.getenv('NOMINATIM_EMAIL', 'contact@example.com')
GEOJSON_CACHE_DIR = os.getenv('GEOJSON_CACHE_DIR', '/data/geojson_cache')
DATABASE_PATH = os.getenv('DATABASE_PATH', '/data/color_communes.db')

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN non defini dans .env")
    exit(1)

# Services
gpx_parser = GpxParser(sample_distance_m=500)
nominatim = NominatimService(email=NOMINATIM_EMAIL, rate_limit_s=2.0)
geojson_svc = GeoJsonService(cache_dir=GEOJSON_CACHE_DIR)
map_svc = MapService(output_dir="/data")
db_svc = DatabaseService(db_path=DATABASE_PATH)
commune_processor = CommuneProcessor('/app/communes_mapping.csv')

# Learning & Validation
learning_svc = None
validation_handler = None
obsidian_reporter = ObsidianReporter(output_dir="/data/wiki-exports")

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /start"""
    user = update.effective_user
    logger.info(f"Commande /start from {user.id}")
    
    await update.message.reply_text(
        f"Bienvenue {user.first_name} ! 🚴\n\n"
        f"Je suis le bot Color_communes.\n"
        f"Envoie-moi un fichier GPX pour voir les communes traversees.\n\n"
        f"Commandes disponibles:\n"
        f"/start — ce message\n"
        f"/help — aide detaillee\n"
        f"/validate — Mode validation interactif [NOUVEAU]\n"
        f"/cumul — carte cumulative\n"
        f"/stats — statistiques\n"
        f"/reset — reinitialiser"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /help"""
    user = update.effective_user
    logger.info(f"Commande /help from {user.id}")

    await update.message.reply_text(
        "📖 **Aide Color_communes**\n\n"
        "1️⃣ **Envoie un GPX** — Je genere une carte des communes traversees\n"
        "2️⃣ **/validate** — Valider communes (doublons, mismatches, corrections)\n"
        "3️⃣ **/cumul** — Voir toutes les communes depuis le debut\n"
        "4️⃣ **/stats** — Stats (communes, departements, sorties)\n"
        "5️⃣ **/history YYYY-MM-DD** — Communes depuis une date\n"
        "6️⃣ **/compare YYYY-MM-DD** — Avant/apres une date pivot\n"
        "7️⃣ **/settings** — Palette couleurs et taille carte\n"
        "8️⃣ **/gpx_list** — Historique des fichiers importes\n"
        "9️⃣ **/reset** — Reinitialiser la base\n\n"
        "Les fichiers acceptes: GPX (Komoot, Strava, Garmin)\n"
        "Colorisation:\n"
        "  🟡 1 passage | 🟠 2-4 passages | 🔴 5-9 passages | 🔴🔴 10+ passages",
        parse_mode='Markdown'
    )

async def cumul_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /cumul — show cumulative map"""
    user = update.effective_user
    logger.info(f"Commande /cumul from {user.id}")

    # Get all communes from database
    communes_cumul = db_svc.get_all_communes()

    if not communes_cumul:
        await update.message.reply_text("❌ Aucune commune enregistrée")
        return

    # Get geojsons for all departments
    depts = sorted(set(c['dept'] for c in communes_cumul.values()))
    geojsons = {}
    for dept in depts:
        gj = geojson_svc.download_geojson(dept)
        if gj:
            geojsons[dept] = gj

    if not geojsons:
        await update.message.reply_text("❌ Erreur GeoJSON")
        return

    # Generate cumulative map
    title = "🚴 Carte cumulative (toutes sorties)"
    result_map = map_svc.generate_map(geojsons, communes_cumul, title=title)

    if not result_map or not result_map[0]:
        await update.message.reply_text("❌ Erreur génération carte")
        return

    png_bytes, rapport = result_map

    # Send
    depts_str = ", ".join(sorted(geojsons.keys()))
    caption = f"✅ Carte cumulative!\n\n🏘️ Total communes: {len(communes_cumul)}\n📍 Départements: {depts_str}"
    if rapport:
        caption += f"\n\n{rapport}"

    await update.message.reply_photo(photo=png_bytes, caption=caption)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /stats — show statistics"""
    user = update.effective_user
    logger.info(f"Commande /stats from {user.id}")

    stats = db_svc.get_stats()

    if not stats:
        await update.message.reply_text("❌ Aucune donnée")
        return

    msg = (
        f"📊 **Statistiques cumulatives**\n\n"
        f"🏘️ Communes totales: {stats['total_communes']}\n"
        f"📍 Départements: {stats['total_depts']}\n"
        f"🚴 Passages cumulés: {stats['total_passages']}\n"
        f"📆 Première visite: {stats['first_visit']}\n"
        f"📆 Dernière visite: {stats['last_visit']}\n\n"
        f"**Top communes:**\n"
    )

    for i, (commune, count) in enumerate(stats['top_communes'][:5], 1):
        msg += f"{i}. {commune} ({count} passages)\n"

    await update.message.reply_text(msg, parse_mode='Markdown')

async def reset_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start reset dialog"""
    user = update.effective_user
    logger.info(f"Commande /reset from {user.id}")

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Oui, réinitialiser", callback_data='reset_confirm'),
         InlineKeyboardButton("Non, annuler", callback_data='reset_cancel')]
    ])
    await update.message.reply_text(
        "⚠️ Attention: réinitialiser la base supprimera TOUTES les communes.\n"
        "Êtes-vous sûr?",
        reply_markup=reply_markup
    )

async def reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle reset confirmation"""
    query = update.callback_query
    if query.data == 'reset_confirm':
        db_svc.reset_database()
        await query.edit_message_text("✅ Base réinitialisée")
        logger.info(f"Database reset by {query.from_user.id}")
    else:
        await query.edit_message_text("❌ Annulé")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /history YYYY-MM-DD — show map from that date onward"""
    user = update.effective_user
    logger.info(f"Commande /history from {user.id}")

    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: /history YYYY-MM-DD\n"
            "Exemple: /history 2026-04-01"
        )
        return

    try:
        from_date = context.args[0]
        datetime.strptime(from_date, '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text("❌ Format invalide. Utilise YYYY-MM-DD")
        return

    communes_hist = db_svc.get_communes_by_date(from_date)
    if not communes_hist:
        await update.message.reply_text(f"❌ Aucune commune trouvée après {from_date}")
        return

    palette = db_svc.get_user_preference(user.id, 'color_palette') or 'classic'
    map_size = db_svc.get_user_preference(user.id, 'map_size') or 'medium'

    depts = sorted(set(c['dept'] for c in communes_hist.values()))
    geojsons = {}
    for dept in depts:
        gj = geojson_svc.download_geojson(dept)
        if gj:
            geojsons[dept] = gj

    if not geojsons:
        await update.message.reply_text("❌ Erreur GeoJSON")
        return

    title = f"🚴 Historique depuis {from_date}"
    result_map = map_svc.generate_map(geojsons, communes_hist, title=title,
                                      palette=palette, map_size=map_size)

    if not result_map or not result_map[0]:
        await update.message.reply_text("❌ Erreur génération carte")
        return

    png_bytes, rapport = result_map

    # Classer par type
    communes_count = sum(1 for c in communes_hist.values() if c.get('type') in ['municipality', 'town', 'city'])
    hamlets_count = sum(1 for c in communes_hist.values() if c.get('type') == 'hamlet')
    location_str = f"🏘️ Communes: {communes_count}"
    if hamlets_count > 0:
        location_str += f" | 🏠 Hameaux: {hamlets_count}"

    caption = f"📅 Historique depuis {from_date}\n{location_str}"
    await update.message.reply_photo(photo=png_bytes, caption=caption)

async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /compare YYYY-MM-DD — compare before/after that date"""
    user = update.effective_user
    logger.info(f"Commande /compare from {user.id}")

    if not context.args or len(context.args) < 1:
        await update.message.reply_text("❌ Usage: /compare YYYY-MM-DD")
        return

    try:
        pivot_date = context.args[0]
        datetime.strptime(pivot_date, '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text("❌ Format invalide. Utilise YYYY-MM-DD")
        return

    communes_before = db_svc.get_communes_in_range('2000-01-01', pivot_date) or {}
    communes_after = db_svc.get_communes_by_date(pivot_date) or {}

    if not communes_before and not communes_after:
        await update.message.reply_text(f"❌ Aucune donnée pour {pivot_date}")
        return

    palette = db_svc.get_user_preference(user.id, 'color_palette') or 'classic'

    all_depts = set()
    if communes_before:
        all_depts.update(c['dept'] for c in communes_before.values())
    if communes_after:
        all_depts.update(c['dept'] for c in communes_after.values())

    geojsons = {}
    for dept in sorted(all_depts):
        gj = geojson_svc.download_geojson(dept)
        if gj:
            geojsons[dept] = gj

    result_map = map_svc.generate_comparison_map(geojsons, communes_before or {},
                                                  communes_after or {}, palette=palette)

    if not result_map or not result_map[0]:
        await update.message.reply_text("❌ Erreur génération carte")
        return

    png_bytes, rapport = result_map

    # Compter avant et après
    before_communes = sum(1 for c in (communes_before or {}).values() if c.get('type') in ['municipality', 'town', 'city'])
    after_communes = sum(1 for c in (communes_after or {}).values() if c.get('type') in ['municipality', 'town', 'city'])
    new_count = after_communes - before_communes if communes_before else after_communes

    caption = (
        f"📊 Comparaison pivot: {pivot_date}\n"
        f"📍 Avant: {before_communes} communes\n"
        f"📍 Après: {after_communes} communes\n"
        f"🆕 Nouvelles: {new_count}"
    )
    await update.message.reply_photo(photo=png_bytes, caption=caption)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /settings — show preferences menu"""
    user = update.effective_user
    logger.info(f"Commande /settings from {user.id}")

    palette_buttons = [
        InlineKeyboardButton("🎨 Classique", callback_data='palette_classic'),
        InlineKeyboardButton("🔥 Vibrant", callback_data='palette_vibrant'),
        InlineKeyboardButton("🌸 Pastel", callback_data='palette_pastel'),
        InlineKeyboardButton("⚫ Gris", callback_data='palette_grayscale'),
    ]

    size_buttons = [
        InlineKeyboardButton("📱 Petit", callback_data='size_small'),
        InlineKeyboardButton("🖥️ Moyen", callback_data='size_medium'),
        InlineKeyboardButton("🖨️ Grand", callback_data='size_large'),
    ]

    reply_markup = InlineKeyboardMarkup([
        palette_buttons,
        size_buttons,
    ])

    current_palette = db_svc.get_user_preference(user.id, 'color_palette') or 'classic'
    current_size = db_svc.get_user_preference(user.id, 'map_size') or 'medium'

    await update.message.reply_text(
        f"⚙️ **Préférences**\n\n"
        f"Palette actuelle: {current_palette}\n"
        f"Taille actuelle: {current_size}\n\n"
        f"Palette de couleurs:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings preferences selection"""
    query = update.callback_query
    user_id = query.from_user.id

    if query.data.startswith('palette_'):
        palette = query.data.replace('palette_', '')
        db_svc.set_user_preference(user_id, 'color_palette', palette)
        await query.edit_message_text(f"✅ Palette définie: {palette}")

    elif query.data.startswith('size_'):
        size = query.data.replace('size_', '')
        db_svc.set_user_preference(user_id, 'map_size', size)
        await query.edit_message_text(f"✅ Taille définie: {size}")

async def gpx_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /gpx_list — show history of imported GPX files"""
    user = update.effective_user
    logger.info(f"Commande /gpx_list from {user.id}")

    history = db_svc.get_gpx_history()

    if not history:
        await update.message.reply_text("❌ Aucun GPX importé")
        return

    msg = "📋 **Historique des GPX importés**\n\n"
    for i, entry in enumerate(history[:20], 1):  # Limiter à 20 derniers
        date_str = entry['processed_at'].split('T')[0] if entry['processed_at'] else "N/A"
        msg += f"{i}. {date_str} | {entry['filename']}\n"
        msg += f"   🏘️ {entry['nb_communes']} communes | 📍 {entry['nb_depts']} depts\n"

    if len(history) > 20:
        msg += f"\n... et {len(history) - 20} autres fichiers"

    await update.message.reply_text(msg, parse_mode='Markdown')

def detect_unmatched_communes(communes: Dict, geojsons: Dict) -> Dict:
    """Détecter communes sans correspondance GeoJSON et chercher proches matches"""
    unmatched = []
    suggestions = {}

    # Construire dict de tous les noms GeoJSON (clé=minuscules, val=original)
    geojson_names_map = {}
    for dept, geojson in geojsons.items():
        if not geojson or 'features' not in geojson:
            continue
        for feature in geojson['features']:
            props = feature.get('properties', {})
            # Essayer plusieurs clés possibles
            name = props.get('nom') or props.get('name') or props.get('commune') or props.get('city') or ''
            if name:
                name_lower = name.lower().strip()
                if name_lower not in geojson_names_map:
                    geojson_names_map[name_lower] = name

    all_geojson_names = list(geojson_names_map.keys())

    for commune_name in communes.keys():
        found = False
        commune_lower = commune_name.lower().strip()

        # Exact match
        if commune_lower in geojson_names_map:
            found = True
        else:
            # Fuzzy match sur tous les GeoJSON
            for dept, geojson in geojsons.items():
                if not geojson or 'features' not in geojson:
                    continue
                for feature in geojson['features']:
                    props = feature.get('properties', {})
                    geojson_name = props.get('nom') or props.get('name') or props.get('commune') or props.get('city') or ''
                    if geojson_name.lower().strip() == commune_lower:
                        found = True
                        break
                if found:
                    break

        if not found:
            unmatched.append(commune_name)

            # Chercher des noms similaires avec cutoff réduit (0.6 au lieu de 0.7)
            close_matches = get_close_matches(
                commune_lower,
                all_geojson_names,
                n=3,
                cutoff=0.6
            )
            if close_matches:
                # Retourner les noms avec casse originale
                suggestions[commune_name] = [geojson_names_map[m] for m in close_matches]
                logger.info(f"Suggestions for {commune_name}: {suggestions[commune_name]}")

    logger.info(f"Unmatched: {len(unmatched)}, Suggestions: {len(suggestions)}")
    return {
        'unmatched': unmatched,
        'suggestions': suggestions
    }

async def validate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler /validate — Validation simplifiée des communes"""
    global learning_svc, validation_handler

    user = update.effective_user
    logger.info(f"🔍 validate_command START from {user.id}")

    try:
        # Vérifier si GPX en cours
        if 'current_gpx' not in context.user_data or 'communes_original' not in context.user_data:
            logger.warning(f"❌ Pas de GPX en cours pour {user.id}")
            reply_method = update.message.reply_text if update.message else update.callback_query.message.reply_text
            await reply_method(
                "❌ Pas de GPX en cours.\n\n"
                "Envoie d'abord un fichier GPX, puis utilise /validate"
            )
            return

        gpx_filename = context.user_data['current_gpx']
        communes = context.user_data['communes_original']
        geojsons = context.user_data['geojsons']
        logger.info(f"📄 GPX: {gpx_filename}, Communes: {len(communes)}, GeoJSON: {len(geojsons)}")

        # Charger et appliquer les corrections sauvegardées
        saved_corrections = db_svc.get_commune_corrections()
        communes_auto_corrected = communes.copy()
        auto_corrections_applied = 0

        for original_name in list(communes_auto_corrected.keys()):
            if original_name in saved_corrections:
                corrected_name = saved_corrections[original_name]
                communes_auto_corrected[corrected_name] = communes_auto_corrected.pop(original_name)
                auto_corrections_applied += 1
                logger.info(f"Correction auto-appliquée: {original_name} → {corrected_name}")

        logger.info(f"🔍 Détection unmatched communes...")
        # Détecter problèmes avec communes corrigées
        result = detect_unmatched_communes(communes_auto_corrected, geojsons)
        unmatched = result['unmatched']
        suggestions = result['suggestions']
        logger.info(f"📊 Unmatched: {len(unmatched)}, Suggestions trouvées: {len(suggestions)}")

    except Exception as e:
        logger.error(f"❌ Erreur validate_command: {e}", exc_info=True)
        reply_method = update.message.reply_text if update.message else update.callback_query.message.reply_text
        await reply_method(f"❌ Erreur validation: {str(e)[:100]}")
        return

    # Déterminer le message à afficher
    reply_method = update.message.reply_text if update.message else update.callback_query.message.reply_text

    if not unmatched:
        msg = "✅ **Validation complète**\n\n"
        msg += f"{len(communes_auto_corrected)} communes validées avec succès !\n"
        if auto_corrections_applied > 0:
            msg += f"\n🧠 {auto_corrections_applied} corrections auto-appliquées"
        msg += "\nAucun problème détecté."

        await reply_method(msg, parse_mode='Markdown')
        return

    # Workflow: approuver une commune à la fois
    msg = f"⚠️ **Validation des communes**\n\n"
    msg += f"**{len(unmatched)} communes à valider**\n\n"

    # Afficher tableau de toutes les communes avec suggestions
    msg += "**TABLEAU - Communes sans JSON / Suggestions:**\n\n"
    msg += "```\n"
    msg += f"{'#':<3} | {'Commune':<30} | {'Suggestion':<30}\n"
    msg += "-" * 68 + "\n"

    for i, comm in enumerate(unmatched[:10], 1):
        sugg = ""
        if comm in suggestions and suggestions[comm]:
            sugg = suggestions[comm][0]  # Première suggestion
        msg += f"{i:<3} | {comm:<30} | {sugg:<30}\n"

    if len(unmatched) > 10:
        msg += f"... et {len(unmatched) - 10} autres\n"

    msg += "```\n\n"

    # Afficher la première commune en détail
    current_idx = 0
    current_commune = unmatched[current_idx]

    msg += f"**VALIDATION #1/{len(unmatched)}** — ❌ **{current_commune}**\n\n"

    if current_commune in suggestions and suggestions[current_commune]:
        msg += "Suggestions proposées:\n"
        for i, sugg in enumerate(suggestions[current_commune], 1):
            msg += f"  {i}. {sugg}\n"
    else:
        msg += "*(Aucune suggestion)*\n"

    # Boutons: approuver avec suggestion ou ignorer
    keyboard_buttons = []
    if current_commune in suggestions and len(suggestions[current_commune]) > 0:
        for i, sugg in enumerate(suggestions[current_commune], 1):
            keyboard_buttons.append([
                InlineKeyboardButton(f"✅ {i}. {sugg}", callback_data=f"validate_approve_{current_idx}_{i-1}")
            ])

    # Ajouter bouton "Ignorer cette commune"
    keyboard_buttons.append([
        InlineKeyboardButton("⏭️ Ignorer et continuer", callback_data=f"validate_skip_{current_idx}")
    ])

    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    logger.info(f"✉️ Envoi message validation: {len(unmatched)} unmatched, {len(keyboard_buttons)} boutons")
    await reply_method(msg, reply_markup=keyboard, parse_mode='Markdown')
    logger.info(f"✅ Message validation envoyé!")

    # Sauvegarder l'état dans le context
    context.user_data['validation_state'] = {
        'unmatched': unmatched,
        'suggestions': suggestions,
        'current_idx': 0,
        'corrections_applied': {},  # {original: corrected}
        'communes_auto_corrected': communes_auto_corrected,
        'geojsons': geojsons
    }
    logger.info(f"✅ État de validation sauvegardé")

async def callback_validate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler callback pour bouton VALIDER"""
    query = update.callback_query
    await query.answer()

    # Lancer /validate command
    await validate_command(update, context)

async def callback_validate_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler pour approuver une correction et passer à la suivante"""
    query = update.callback_query
    await query.answer()

    # Parser callback: validate_approve_<idx>_<sugg_idx>
    parts = query.data.split('_')
    if len(parts) < 4:
        await query.edit_message_text("❌ Erreur parsing")
        return

    current_idx = int(parts[2])
    sugg_idx = int(parts[3])

    state = context.user_data.get('validation_state', {})
    if not state:
        await query.edit_message_text("❌ État de validation manquant")
        return

    unmatched = state['unmatched']
    suggestions = state['suggestions']
    corrections_applied = state['corrections_applied']

    # Appliquer la correction
    current_commune = unmatched[current_idx]
    if current_commune in suggestions and sugg_idx < len(suggestions[current_commune]):
        corrected_name = suggestions[current_commune][sugg_idx]
        corrections_applied[current_commune] = corrected_name
        logger.info(f"Correction approuvée: {current_commune} → {corrected_name}")

    # Passer à la commune suivante
    next_idx = current_idx + 1

    if next_idx >= len(unmatched):
        # Fin de validation — régénérer la carte
        await _finish_validation(query, context, corrections_applied)
    else:
        # Afficher la commune suivante
        await _show_next_commune(query, context, next_idx)

async def callback_validate_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler pour ignorer une commune et passer à la suivante"""
    query = update.callback_query
    await query.answer()

    # Parser callback: validate_skip_<idx>
    parts = query.data.split('_')
    if len(parts) < 3:
        await query.edit_message_text("❌ Erreur parsing")
        return

    current_idx = int(parts[2])
    logger.info(f"Commune {current_idx} ignorée")

    state = context.user_data.get('validation_state', {})
    if not state:
        await query.edit_message_text("❌ État de validation manquant")
        return

    unmatched = state['unmatched']
    next_idx = current_idx + 1

    if next_idx >= len(unmatched):
        # Fin de validation
        corrections_applied = state['corrections_applied']
        await _finish_validation(query, context, corrections_applied)
    else:
        # Afficher la commune suivante
        await _show_next_commune(query, context, next_idx)

async def _show_next_commune(query, context, idx: int):
    """Afficher la commune à l'index idx"""
    state = context.user_data.get('validation_state', {})
    unmatched = state['unmatched']
    suggestions = state['suggestions']

    if idx >= len(unmatched):
        return

    state['current_idx'] = idx
    current_commune = unmatched[idx]

    msg = f"⚠️ **Validation des communes** — #{idx + 1}/{len(unmatched)}\n\n"
    msg += f"❌ **{current_commune}**\n\n"

    if current_commune in suggestions and suggestions[current_commune]:
        msg += "Suggestions:\n"
        for i, sugg in enumerate(suggestions[current_commune], 1):
            msg += f"  {i}. {sugg}\n"
    else:
        msg += "*(Aucune suggestion)*\n"

    keyboard_buttons = []
    if current_commune in suggestions and suggestions[current_commune]:
        for i, sugg in enumerate(suggestions[current_commune], 1):
            keyboard_buttons.append([
                InlineKeyboardButton(f"✅ {i}. {sugg}", callback_data=f"validate_approve_{idx}_{i-1}")
            ])

    keyboard_buttons.append([
        InlineKeyboardButton("⏭️ Ignorer et continuer", callback_data=f"validate_skip_{idx}")
    ])

    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    await query.edit_message_text(msg, reply_markup=keyboard, parse_mode='Markdown')

async def _finish_validation(query, context, corrections_applied: dict):
    """Régénérer la carte et finir la validation"""
    state = context.user_data.get('validation_state', {})
    communes_auto_corrected = state['communes_auto_corrected'].copy()
    geojsons = state['geojsons']
    gpx_filename = context.user_data.get('current_gpx')

    # Appliquer les corrections approuvées
    for original, corrected in corrections_applied.items():
        if original in communes_auto_corrected:
            communes_auto_corrected[corrected] = communes_auto_corrected.pop(original)
            # Sauvegarder la correction en DB
            db_svc.save_commune_correction(original, corrected)
            logger.info(f"Correction sauvegardée en DB: {original} → {corrected}")

    palette = context.user_data.get('palette', 'classic')
    map_size = context.user_data.get('map_size', 'medium')

    await query.edit_message_text("🔄 **Régénération de la carte...**")

    try:
        result_map = map_svc.generate_map(
            geojsons,
            communes_auto_corrected,
            title=f"🚴 {gpx_filename} [CORRIGÉ]",
            palette=palette,
            map_size=map_size
        )

        if result_map and result_map[0]:
            png_bytes, _ = result_map

            await query.message.reply_photo(
                photo=png_bytes,
                caption=(
                    f"✅ **Validation terminée !**\n\n"
                    f"📝 Corrections approuvées: {len(corrections_applied)}\n"
                    f"🏘️ Communes validées: {len(communes_auto_corrected)}"
                )
            )

            await query.edit_message_text(
                f"✅ **Carte régénérée!**\n\n"
                f"✓ {len(corrections_applied)} corrections appliquées\n"
                f"✓ {len(corrections_applied)} corrections sauvegardées pour futurs GPX"
            )
        else:
            await query.edit_message_text("❌ Erreur génération carte")

    except Exception as e:
        logger.error(f"Erreur finish_validation: {e}")
        await query.edit_message_text(f"❌ Erreur: {str(e)[:100]}")

async def callback_validate_apply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler legacy - pas utilisé avec nouveau workflow"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ce bouton n'existe plus. Utilise le workflow approuvation une par une.")

async def callback_validate_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler pour rejeter les corrections"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "❌ Validation rejetée\n\n"
        "Le GPX conserve ses données originales"
    )

async def handle_gpx(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler reception fichier GPX"""
    user = update.effective_user
    message = update.message
    
    if message.document:
        file = message.document
        logger.info(f"GPX recu from {user.id}: {file.file_name}")
        
        # Verifier extension
        if not file.file_name.lower().endswith('.gpx'):
            await update.message.reply_text(
                "❌ Fichier invalide.\n"
                "Acceptes: .gpx seulement"
            )
            return
        
        # Envoyer message de traitement
        processing_msg = await update.message.reply_text(
            "⏳ Traitement en cours...\n"
            f"📄 Fichier: {file.file_name}\n"
            f"📦 Taille: {file.file_size / 1024:.1f} KB\n\n"
            f"Phase 1: Parsing GPX...\n"
            f"Phase 2: Reverse geocoding...\n"
            f"Phase 3: Cache GeoJSON...\n"
            f"Phase 4: Génération carte..."
        )
        
        try:
            # Telecharger le fichier
            gpx_file = await context.bot.get_file(file.file_id)
            gpx_bytes = await gpx_file.download_as_bytearray()

            # Calculer hash MD5 du fichier
            file_hash = hashlib.md5(gpx_bytes).hexdigest()
            logger.info(f"File hash: {file_hash}")

            # TODO: Vérification doublon EN PAUSE — permet retraitement du même fichier
            # if db_svc.is_file_processed(file_hash):
            #     await processing_msg.edit_text(...)
            #     return

            # Phase 3: Parser le GPX
            result = gpx_parser.parse(bytes(gpx_bytes))
            
            if not result:
                await update.message.reply_text("❌ Erreur lors du parsing du GPX")
                return
            
            # Phase 4: Reverse geocoding des points échantillonnés
            communes_raw = nominatim.batch_geocode(result['sampled_points'])

            if not communes_raw:
                await update.message.reply_text("❌ Aucune commune trouvée")
                return

            # Phase 4.5: Appliquer commune_processor (Phase 2) pour correction/validation
            communes = {}
            corrections_log = []
            rejected_count = 0

            for commune_name in communes_raw.keys():
                processed = commune_processor.process(commune_name)

                if processed.status in (ProcessStatus.VALID, ProcessStatus.CORRECTED):
                    # Commune valide ou corrigée
                    final_name = processed.corrected_name or commune_name
                    communes[final_name] = communes_raw[commune_name]

                    if processed.status == ProcessStatus.CORRECTED:
                        corrections_log.append(f"{commune_name} → {final_name}")
                        logger.info(f"Correction appliquée: {commune_name} → {final_name}")

                elif processed.status == ProcessStatus.UNKNOWN:
                    # Approche hybride: si Nominatim l'a trouvée, on l'accepte quand même
                    communes[commune_name] = communes_raw[commune_name]
                    logger.info(f"Commune acceptée (Nominatim valide): {commune_name}")

                elif processed.status == ProcessStatus.REJECTED:
                    rejected_count += 1
                    logger.info(f"Commune rejetée: {commune_name} ({processed.reason})")

            if corrections_log:
                logger.info(f"🔧 Phase 2 - {len(corrections_log)} corrections appliquées")
            if rejected_count > 0:
                logger.info(f"🚫 Phase 2 - {rejected_count} communes rejetées")

            # Générer rapport Phase 2 (correspondance communes traitées)
            import csv
            from datetime import datetime as dt
            report_filename = f"/data/phase2_report_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
            try:
                with open(report_filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['commune_original', 'statut', 'commune_finale', 'raison'])
                    for commune_name in communes_raw.keys():
                        processed = commune_processor.process(commune_name)
                        final_name = processed.corrected_name or commune_name
                        writer.writerow([commune_name, processed.status.value, final_name, processed.reason or ''])
                logger.info(f"Rapport Phase 2 sauvegardé: {report_filename}")
            except Exception as e:
                logger.error(f"Erreur génération rapport Phase 2: {e}")
            # 🆕 GÉNÉRER CSV COMMUNES NOMINATIM (APPROCHE HYBRIDE)
            nominatim_found = []
            for commune_name in communes_raw.keys():
                processed = commune_processor.process(commune_name)

                # Capturer communes UNKNOWN acceptées via Nominatim (hybrid)
                if processed.status == ProcessStatus.UNKNOWN:
                    coords = communes_raw[commune_name]
                    nominatim_found.append({
                        'commune': commune_name,
                        'latitude': coords.get('lat', ''),
                        'longitude': coords.get('lon', ''),
                        'method': 'nominatim',
                        'geojson_status': 'missing'
                    })

            # Écrire CSV communes_nominatim_found.csv
            if nominatim_found:
                try:
                    nominatim_csv = f"/data/communes_nominatim_found_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    with open(nominatim_csv, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=['commune', 'latitude', 'longitude', 'method', 'geojson_status'])
                        writer.writeheader()
                        writer.writerows(nominatim_found)

                    logger.info(f"✅ CSV communes Nominatim généré: {nominatim_csv}")
                    logger.info(f"   {len(nominatim_found)} communes trouvées mais non en GeoJSON")

                except Exception as e:
                    logger.error(f"❌ Erreur génération CSV Nominatim: {e}")


            if not communes:
                await update.message.reply_text("❌ Aucune commune valide après correction")
                return

            # Phase 4.5: Enregistrer dans la base de données (cumul)
            db_svc.upsert_communes(communes)
            
            # Phase 5: Télécharger et cacher les GeoJSON
            geojsons = geojson_svc.get_geojson_for_communes(communes)
            
            if not geojsons:
                await update.message.reply_text("❌ Erreur GeoJSON")
                return
            
            # Phase 6: Générer la carte PNG
            # Titre avec date du GPX + date du jour
            date_gpx = result['metadata'].get('date_start', datetime.now().strftime('%d/%m/%Y'))
            date_today = datetime.now().strftime('%d/%m/%Y')
            if date_gpx == date_today:
                title = f"🚴 Sortie du {date_gpx}"
            else:
                title = f"🚴 Sortie du {date_gpx} (générée le {date_today})"
            result_map = map_svc.generate_map(geojsons, communes, title=title)

            if not result_map or not result_map[0]:
                await update.message.reply_text("❌ Erreur génération carte")
                return

            png_bytes, rapport = result_map

            # Détecter communes sans correspondance GeoJSON
            unmatched_data = detect_unmatched_communes(communes, geojsons)
            unmatched = unmatched_data['unmatched']

            # Sauvegarder et envoyer
            filename = f"sortie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            map_svc.save_png(png_bytes, filename)

            # Envoyer la carte PNG
            depts_str = ", ".join(sorted(geojsons.keys()))

            # Classer par type (commune, hamlet, village, etc.)
            communes_count = sum(1 for c in communes.values() if c.get('type') in ['municipality', 'town', 'city'])
            hamlets_count = sum(1 for c in communes.values() if c.get('type') == 'hamlet')
            villages_count = sum(1 for c in communes.values() if c.get('type') == 'village')

            # Build location string
            location_str = f"🏘️ Communes: {communes_count}"
            if hamlets_count > 0:
                location_str += f" | 🏠 Hameaux: {hamlets_count}"
            if villages_count > 0:
                location_str += f" | 🏞️ Villages: {villages_count}"

            caption = (
                f"✅ Carte générée!\n\n"
                f"{location_str}\n"
                f"📍 Départements: {depts_str}\n"
                f"📏 Points GPS: {result['nb_points']} → {result['nb_sampled']} (500m)\n\n"
                f"Colorisation: 🟡 1 | 🟠 2-4 | 🔴 5-9 | 🔴🔴 10+"
            )
            if rapport:
                caption += f"\n\n{rapport}"

            await update.message.reply_photo(
                photo=png_bytes,
                caption=caption
            )

            # Afficher rapport non-matches si nécessaire
            if unmatched:
                unmatched_msg = "⚠️ **Communes SANS correspondance GeoJSON:**\n\n"
                for comm in unmatched[:10]:
                    unmatched_msg += f"❌ {comm}\n"
                if len(unmatched) > 10:
                    unmatched_msg += f"\n... et {len(unmatched) - 10} autres"

                await update.message.reply_text(unmatched_msg, parse_mode='Markdown')

            # Sauvegarder pour validation interactive
            context.user_data['current_gpx'] = file.file_name
            context.user_data['communes_original'] = communes
            context.user_data['geojsons'] = geojsons
            context.user_data['palette'] = db_svc.get_user_preference(user.id, 'color_palette') or 'classic'
            context.user_data['map_size'] = db_svc.get_user_preference(user.id, 'map_size') or 'medium'

            # Enregistrer fichier comme traité (avec stats)
            db_svc.register_file(file_hash, file.file_name, len(communes), len(geojsons))

            await update.message.reply_text(
                f"✅ Traité!\n\n{file.file_name}\n{len(communes)} communes"
            )

            # Mettre à jour message de traitement
            await processing_msg.edit_text("✅ Carte envoyée!")

            logger.info(f"Traitement complet: {len(communes)} communes, {len(geojsons)} GeoJSON, PNG généré")
        
        except Exception as e:
            logger.error(f"Erreur traitement GPX: {e}")
            await update.message.reply_text(f"❌ Erreur: {str(e)[:100]}")
    else:
        await update.message.reply_text(
            "❌ Je n'accepte que les fichiers GPX.\n"
            "Envoie un fichier GPX (Komoot, Strava, Garmin)"
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gerer les erreurs"""
    logger.error(f"Exception while handling an update: {context.error}")

# Handlers pour les STEPs de validation
async def handle_step2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler STEP2 — Doublons"""
    global validation_handler
    if validation_handler:
        await validation_handler._handle_step2_duplicate(update, context)

async def handle_step3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler STEP3 — Multi-depts"""
    global validation_handler
    if validation_handler:
        await validation_handler._handle_step3_dept(update, context)

async def handle_step4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler STEP4 — GeoJSON matching"""
    global validation_handler
    if validation_handler:
        await validation_handler._handle_step4_solution(update, context)

async def handle_step5_apply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler STEP5 — Apply"""
    global validation_handler
    if validation_handler:
        await validation_handler._handle_step5_apply(update, context)

async def handle_step5_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler STEP5 — Reject"""
    global validation_handler
    if validation_handler:
        await validation_handler._handle_step5_reject(update, context)

def auto_import_communes():
    """Auto-import communes si communes_a_importer.csv existe"""
    import_file = Path('/app/communes_a_importer.csv')

    if not import_file.exists():
        logger.info("✓ Pas de fichier d'import à traiter")
        return

    logger.info(f"🔄 Auto-import communes détecté: {import_file}")
    try:
        importer = CommunesImporter()
        result = importer.import_csv(str(import_file))

        if result.get('error'):
            logger.error(f"❌ Erreur import: {result['error']}")
        else:
            logger.info(f"✅ Import réussi: {result.get('added', 0)} communes ajoutées")
            logger.info(f"   Total: {result.get('total', 0)} | Doublons: {result.get('duplicates', 0)} | Invalides: {result.get('invalid', 0)}")

            # Supprimer le fichier après import réussi
            import_file.unlink()
            logger.info(f"📁 Fichier supprimé après import")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'auto-import: {e}")

def main() -> None:
    """Demarrer le bot"""
    logger.info(f"🤖 Bot Color_communes demarrage...")
    logger.info(f"Token: {TELEGRAM_BOT_TOKEN[:20]}...")
    logger.info(f"User ID: {TELEGRAM_USER_ID}")
    logger.info(f"Échantillonnage GPX: 500m")
    logger.info(f"Nominatim email: {NOMINATIM_EMAIL}")
    logger.info(f"Cache GeoJSON: {GEOJSON_CACHE_DIR}")
    logger.info(f"Database: {DATABASE_PATH}")
    
    # Creer application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers commandes
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("validate", validate_command))
    application.add_handler(CommandHandler("cumul", cumul_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("reset", reset_start))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("compare", compare_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("gpx_list", gpx_list_command))

    # Handler fichiers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_gpx))

    # Callback handlers (reset + settings + validation)
    application.add_handler(CallbackQueryHandler(reset_callback, pattern='^reset_'))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern='^(palette_|size_)'))
    application.add_handler(CallbackQueryHandler(callback_validate, pattern='^action_validate$'))
    application.add_handler(CallbackQueryHandler(callback_validate_approve, pattern='^validate_approve_'))
    application.add_handler(CallbackQueryHandler(callback_validate_skip, pattern='^validate_skip_'))
    application.add_handler(CallbackQueryHandler(callback_validate_apply, pattern='^validate_apply$'))
    application.add_handler(CallbackQueryHandler(callback_validate_reject, pattern='^validate_reject$'))

    # Error handler
    application.add_error_handler(error_handler)

    # Auto-import communes si le fichier existe
    auto_import_communes()

    # Auto-enrichissement GeoJSON communes manquantes
    logger.info("🔄 Vérification enrichissement GeoJSON...")
    try:
        ensure_communes_enriched()
    except Exception as e:
        logger.error(f"⚠️  Auto-enrich échoué: {e}")
        # Continue quand même (non-bloquant)

    # Demarrer le bot
    logger.info("✅ Bot Color_communes pret!")
    logger.info("Phase 6: Génération carte PNG actif (geopandas + matplotlib)")
    logger.info("Phase 7: Base SQLite cumulative actif (cumul, stats, reset)")
    logger.info("Phase 8: Commandes avancees actives (history, compare, settings)")
    logger.info("En attente de messages...")
    application.run_polling()

if __name__ == '__main__':
    main()
