#!/usr/bin/env python3
"""
Gestion des callbacks Telegram pour validation interactive
Traite les réponses utilisateur pour chaque STEP
"""

import logging
from typing import Dict, List, Callable
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class ValidationHandler:
    """Gère les callbacks Telegram pour validation communes"""

    def __init__(self, learning_svc, db_svc, map_svc):
        """
        Args:
            learning_svc: LearningService instance
            db_svc: DatabaseService instance
            map_svc: MapService instance
        """
        self.learning = learning_svc
        self.db = db_svc
        self.map = map_svc

    # ============ STEP 2 : Doublons ============

    async def _handle_step2_duplicate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Utilisateur choisit lequel garder (Cravanche 90300 vs 90000)
        Data: step2_<commune_name>_<chosen_code>
        """
        query = update.callback_query
        await query.answer()

        # Parser callback
        parts = query.data.split("_", 2)  # ["step2", commune_name, code]
        if len(parts) < 3:
            await query.edit_message_text("❌ Erreur parsing doublon")
            return

        commune_name = parts[1]
        chosen_code = parts[2]

        if chosen_code == "ignore":
            logger.info(f"STEP 2: Doublon '{commune_name}' ignoré")
            correction = {
                'type': 'duplicate_ignored',
                'commune': commune_name
            }
            await query.edit_message_text(f"❌ {commune_name} — Les deux versions ignorées")
        else:
            logger.info(f"STEP 2: Doublon '{commune_name}' → Garder {chosen_code}")
            correction = {
                'type': 'duplicate_resolved',
                'commune': commune_name,
                'chosen_postcode': chosen_code
            }
            await query.edit_message_text(f"✅ {commune_name} ({chosen_code}) — Gardé")

        # Enregistrer correction
        self.learning.step2_apply_duplicate_choice(commune_name, chosen_code if chosen_code != "ignore" else None)

        # Continuer vers STEP 3
        await self._continue_to_step3(query, context)

    # ============ STEP 3 : Mélange Depts ============

    async def _handle_step3_dept(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Utilisateur choisit département correct
        Data: step3_<commune_name>_<chosen_dept>
        """
        query = update.callback_query
        await query.answer()

        parts = query.data.split("_")
        if len(parts) < 3:
            await query.edit_message_text("❌ Erreur parsing dept")
            return

        commune_name = "_".join(parts[1:-1])
        chosen_dept = parts[-1]

        logger.info(f"STEP 3: '{commune_name}' → Dept {chosen_dept}")

        self.learning.step3_apply_dept_choice(commune_name, chosen_dept)

        await query.edit_message_text(f"✅ {commune_name} — Dept {chosen_dept}")

        # Continuer vers STEP 4
        await self._continue_to_step4(query, context)

    # ============ STEP 4 : GeoJSON Matching ============

    async def _handle_step4_solution(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Utilisateur choisit solution pour commune non-matchée
        Data: step4_<commune_name>_<solution_id>_<optional_detail>
        """
        query = update.callback_query
        await query.answer()

        parts = query.data.split("_", 3)
        if len(parts) < 3:
            await query.edit_message_text("❌ Erreur parsing solution")
            return

        commune_name = parts[1]
        solution_id = parts[2]
        detail = parts[3] if len(parts) > 3 else None

        # Map solution to label
        solutions_map = {
            'A': '➕ Ajouter dans GeoJSON',
            'B': '✏️ Corriger code postal',
            'C': '🔤 Normaliser nom',
            'D': '❌ No Match',
            'E': '📝 Issue Obsidian'
        }

        logger.info(f"STEP 4: '{commune_name}' → Solution {solution_id}")

        # Si solution B ou C, demander détail
        if solution_id == 'B':
            await query.edit_message_text(
                f"✏️ {commune_name}\n\nNouveau code postal?"
            )
            context.user_data['awaiting_postcode'] = commune_name
            return

        elif solution_id == 'C':
            await query.edit_message_text(
                f"🔤 {commune_name}\n\nNom correct dans GeoJSON?"
            )
            context.user_data['awaiting_commune_name'] = commune_name
            return

        # Autres solutions : enregistrer directement
        self.learning.step4_apply_solution(commune_name, solution_id, detail)
        await query.edit_message_text(
            f"✅ {commune_name}\n{solutions_map.get(solution_id, solution_id)}"
        )

        # Continuer vers STEP 5
        await self._continue_to_step5(query, context)

    # ============ STEP 5 : Résumé & Apply ============

    async def _handle_step5_apply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Utilisateur confirme : APPLIQUER toutes les corrections
        🔄 Retraiter GPX complet
        """
        query = update.callback_query
        await query.answer()

        gpx_filename = context.user_data.get('current_gpx')
        if not gpx_filename:
            await query.edit_message_text("❌ Erreur: GPX non trouvé")
            return

        corrections = self.learning.get_corrections()
        logger.info(f"STEP 5: Applying {len(corrections)} corrections to {gpx_filename}")

        # Afficher progression
        processing_msg = await query.message.reply_text(
            "🔄 **RETRAITEMENT GPX**\n\n"
            "1️⃣ Supprimer doublons\n"
            "2️⃣ Corriger codes postaux\n"
            "3️⃣ Revalider GeoJSON\n"
            "4️⃣ Générer nouvelle carte\n"
            "5️⃣ Comparaison AVANT/APRÈS\n\n"
            "Veuillez patienter..."
        )

        try:
            # 1. Appliquer corrections en DB
            for correction in corrections:
                self.db.apply_validation_correction(gpx_filename, correction)
                logger.info(f"Applied correction: {correction['type']}")

            # 2. Log retraitement
            self.db.log_reprocessing(gpx_filename, corrections)

            # Récupérer communes originales vs corrigées
            communes_original = context.user_data.get('communes_original', [])
            communes_final = self.db.get_communes_from_gpx(gpx_filename)

            # 3. Générer nouvelle carte
            geojsons = context.user_data.get('geojsons')
            png_new, _ = self.map.generate_map(
                geojsons,
                {c['name']: c for c in communes_final},
                title=f"{gpx_filename} [CORRIGÉ]",
                palette=context.user_data.get('palette', 'classic'),
                map_size=context.user_data.get('map_size', 'medium')
            )

            # 4. Générer comparaison
            png_comparison, _ = self.map.generate_comparison_map(
                geojsons,
                communes_before={c['name']: c for c in communes_original},
                communes_after={c['name']: c for c in communes_final},
                palette=context.user_data.get('palette', 'classic')
            )

            # 5. Envoyer résultats
            await processing_msg.edit_text("✅ RETRAITEMENT TERMINÉ\n\nGénération images...")

            # Carte corrigée
            if png_new:
                self.map.save_png(png_new, f"{gpx_filename}_corrected.png")
                await query.message.reply_document(
                    open(f"/data/{gpx_filename}_corrected.png", 'rb'),
                    caption=f"✅ **Carte Corrigée**\n{len(communes_final)} communes"
                )

            # Comparaison
            if png_comparison:
                self.map.save_png(png_comparison, f"{gpx_filename}_comparison.png")
                await query.message.reply_document(
                    open(f"/data/{gpx_filename}_comparison.png", 'rb'),
                    caption="📊 **Comparaison AVANT / APRÈS**"
                )

            # Résumé
            nb_removed = len(communes_original) - len(communes_final)
            await query.message.reply_text(
                f"✅ **VALIDATION TERMINÉE**\n\n"
                f"📊 Résumé:\n"
                f"  • Communes initiales: {len(communes_original)}\n"
                f"  • Communes finales: {len(communes_final)}\n"
                f"  • Doublons supprimés: {nb_removed}\n"
                f"  • Corrections appliquées: {len(corrections)}\n\n"
                f"✅ Carte générée\n"
                f"✅ DB mise à jour\n"
                f"✅ Prêt pour production!"
            )

            logger.info(f"✅ GPX {gpx_filename} validation terminée")

        except Exception as e:
            logger.error(f"❌ Erreur retraitement: {e}", exc_info=True)
            await processing_msg.edit_text(f"❌ **ERREUR**\n\n{str(e)}")

    async def _handle_step5_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Utilisateur rejette les corrections"""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "❌ Validation annulée\n\n"
            "GPX conservé sans modifications"
        )

        self.learning.reset()
        logger.info("Validation rejected by user")

    # ============ Navigation ============

    async def _continue_to_step3(self, query, context):
        """Naviguer vers STEP 3"""
        # Logique : vérifier s'il y a d'autres doublons
        # Pour simplifier : aller à STEP 3 directement
        await query.message.reply_text(
            "⏭️ Passage à STEP 3...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Continuer", callback_data="step3_start")]
            ])
        )

    async def _continue_to_step4(self, query, context):
        """Naviguer vers STEP 4"""
        await query.message.reply_text(
            "⏭️ Passage à STEP 4...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Continuer", callback_data="step4_start")]
            ])
        )

    async def _continue_to_step5(self, query, context):
        """Naviguer vers STEP 5"""
        await query.message.reply_text(
            "⏭️ Passage à STEP 5...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Résumé", callback_data="step5_show")]
            ])
        )

    # ============ Utilitaires ============

    def build_duplicate_keyboard(self, variants: List[Dict]) -> InlineKeyboardMarkup:
        """Créer clavier pour choix doublon"""
        keyboard = InlineKeyboardMarkup()

        for variant in variants:
            code = variant.get('postcode', '?')
            keyboard.add(
                InlineKeyboardButton(
                    f"✓ Garder ({code})",
                    callback_data=f"step2_{variant['name']}_{code}"
                )
            )

        keyboard.add(
            InlineKeyboardButton(
                "❌ Ignorer les deux",
                callback_data=f"step2_{variants[0]['name']}_ignore"
            )
        )

        return keyboard

    def build_solutions_keyboard(self, commune_name: str) -> InlineKeyboardMarkup:
        """Créer clavier pour 5 solutions matching"""
        keyboard = InlineKeyboardMarkup()

        solutions = [
            ('A', '➕ Ajouter GeoJSON'),
            ('B', '✏️ Corriger code postal'),
            ('C', '🔤 Normaliser nom'),
            ('D', '❌ No Match'),
            ('E', '📝 Issue Obsidian'),
        ]

        for sol_id, sol_label in solutions:
            keyboard.add(
                InlineKeyboardButton(
                    sol_label,
                    callback_data=f"step4_{commune_name}_{sol_id}"
                )
            )

        return keyboard
