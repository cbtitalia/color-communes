#!/usr/bin/env python3
"""
Service d'apprentissage communes — 5 STEPS interactifs
À intégrer dans Color_communes
"""

import logging
from typing import Dict, List, Tuple
from collections import defaultdict
import unicodedata

logger = logging.getLogger(__name__)

class LearningService:
    """Gestion validation communes interactif"""

    def __init__(self, gdf_communes: Dict):
        """
        Args:
            gdf_communes: GeoDataFrame communes par département
        """
        self.gdf_communes = gdf_communes
        self.current_step = 0
        self.corrections = []

    # ============ STEP 1 : Extraction ============

    def step1_extraction(self, communes_extracted: List[Dict]) -> Dict:
        """
        STEP 1 : Afficher communes extraites brutes
        """
        self.current_step = 1

        logger.info(f"STEP 1: {len(communes_extracted)} communes extraites")

        return {
            'step': 1,
            'communes': communes_extracted,
            'nb_communes': len(communes_extracted),
            'message': f"✅ STEP 1/5 — Extraction\n\n{len(communes_extracted)} communes trouvées",
            'action': 'CONTINUER'
        }

    # ============ STEP 2 : Doublons ============

    def step2_detect_duplicates(self, communes: List[Dict]) -> Dict:
        """
        STEP 2 : Détecter doublons (même nom, codes postaux différents)
        """
        self.current_step = 2

        duplicates = defaultdict(list)
        for comm in communes:
            key = comm['name'].lower()
            duplicates[key].append(comm)

        issues = {k: v for k, v in duplicates.items() if len(v) > 1}

        if not issues:
            logger.info("STEP 2: Aucun doublon")
            return {
                'step': 2,
                'has_issues': False,
                'message': "✅ STEP 2/5 — Doublons\n\nAucun doublon détecté",
                'action': 'CONTINUER'
            }

        logger.warning(f"STEP 2: {len(issues)} doublons détectés")

        return {
            'step': 2,
            'has_issues': True,
            'issues': issues,
            'nb_issues': len(issues),
            'message': f"⚠️ STEP 2/5 — Doublons\n\n{len(issues)} doublons détectés",
            'action': 'VALIDER_UN_PAR_UN'
        }

    def step2_apply_duplicate_choice(self, commune_name: str, chosen_postcode: str):
        """
        Utilisateur choisit lequel garder
        """
        self.corrections.append({
            'type': 'duplicate',
            'commune': commune_name,
            'chosen_postcode': chosen_postcode
        })
        logger.info(f"STEP 2: Doublon '{commune_name}' résolu → {chosen_postcode}")

    # ============ STEP 3 : Mélange Départements ============

    def step3_multi_dept(self, communes_clean: List[Dict]) -> Dict:
        """
        STEP 3 : Détecter communes listées sous 2+ depts
        """
        self.current_step = 3

        by_name = defaultdict(list)
        for comm in communes_clean:
            key = comm['name'].lower()
            by_name[key].append(comm['dept'])

        issues = {k: list(set(v)) for k, v in by_name.items() if len(set(v)) > 1}

        if not issues:
            logger.info("STEP 3: Pas de mélange départements")
            return {
                'step': 3,
                'has_issues': False,
                'message': "✅ STEP 3/5 — Mélange Depts\n\nAucun mélange détecté",
                'action': 'CONTINUER'
            }

        logger.warning(f"STEP 3: {len(issues)} communes multi-depts")

        return {
            'step': 3,
            'has_issues': True,
            'issues': issues,
            'nb_issues': len(issues),
            'message': f"⚠️ STEP 3/5 — Mélange Depts\n\n{len(issues)} communes sous 2+ depts",
            'action': 'VALIDER_UN_PAR_UN'
        }

    def step3_apply_dept_choice(self, commune_name: str, chosen_dept: str):
        """
        Utilisateur choisit département correct
        """
        self.corrections.append({
            'type': 'multi_dept',
            'commune': commune_name,
            'chosen_dept': chosen_dept
        })
        logger.info(f"STEP 3: '{commune_name}' → Dept {chosen_dept}")

    # ============ STEP 4 : GeoJSON Matching ============

    def step4_geojson_matching(self, communes_final: List[Dict]) -> Dict:
        """
        STEP 4 : Vérifier matching avec GeoJSON
        """
        self.current_step = 4

        unmatched = []
        for comm in communes_final:
            if not self._match_in_geojson(comm['name'], comm.get('dept')):
                unmatched.append(comm)

        if not unmatched:
            logger.info("STEP 4: Tous les matching OK")
            return {
                'step': 4,
                'has_issues': False,
                'message': "✅ STEP 4/5 — GeoJSON Matching\n\nTous les communes matchent",
                'action': 'CONTINUER'
            }

        logger.warning(f"STEP 4: {len(unmatched)} communes non-matchées")

        return {
            'step': 4,
            'has_issues': True,
            'unmatched': unmatched,
            'nb_issues': len(unmatched),
            'message': f"❌ STEP 4/5 — GeoJSON Matching\n\n{len(unmatched)} communes non-matchées",
            'action': 'VALIDER_UN_PAR_UN'
        }

    def step4_propose_solutions(self, commune: Dict) -> Dict:
        """
        Proposer 5 solutions pour commune non-matchée
        """
        return {
            'commune': commune['name'],
            'postcode': commune.get('postcode'),
            'dept': commune.get('dept'),
            'solutions': [
                {
                    'id': 'A',
                    'label': '➕ Ajouter dans GeoJSON',
                    'description': f"Ajouter '{commune['name']}' au GeoJSON dept {commune.get('dept')}"
                },
                {
                    'id': 'B',
                    'label': '✏️ Corriger code postal',
                    'description': f"Code actuel: {commune.get('postcode')} → Nouveau: ?"
                },
                {
                    'id': 'C',
                    'label': '🔤 Normaliser nom',
                    'description': f"Chercher variante (accents, tirets): ?"
                },
                {
                    'id': 'D',
                    'label': '❌ Marquer No Match',
                    'description': "Accepter que cette commune ne match pas"
                },
                {
                    'id': 'E',
                    'label': '📝 Créer Issue Obsidian',
                    'description': "Signaler pour investigation ultérieure"
                }
            ]
        }

    def step4_apply_solution(self, commune_name: str, solution_id: str, detail: str = None):
        """
        Utilisateur choisit solution
        """
        self.corrections.append({
            'type': 'geojson_matching',
            'commune': commune_name,
            'solution': solution_id,
            'detail': detail
        })
        logger.info(f"STEP 4: '{commune_name}' → Solution {solution_id}")

    # ============ STEP 5 : Résumé ============

    def step5_summary(self, communes_final: List[Dict]) -> Dict:
        """
        STEP 5 : Résumé final + validation
        """
        self.current_step = 5

        return {
            'step': 5,
            'nb_communes': len(communes_final),
            'nb_corrections': len(self.corrections),
            'corrections_list': self.corrections,
            'message': f"✅ STEP 5/5 — Résumé\n\n{len(communes_final)} communes finales\n{len(self.corrections)} corrections appliquées",
            'action': 'SAUVEGARDER_OU_REJETER'
        }

    # ============ Utilitaires ============

    def _normalize_name(self, name: str) -> str:
        """Normaliser nom pour matching robuste"""
        if not name:
            return ""
        # Enlever accents
        normalized = unicodedata.normalize('NFD', name)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        # Minuscules, supprimer espaces/tirets
        normalized = normalized.lower().replace(' ', '').replace('-', '').replace("'", '')
        return normalized

    def _match_in_geojson(self, commune_name: str, dept: str) -> bool:
        """Vérifier si commune existe dans GeoJSON"""
        if dept not in self.gdf_communes:
            return False

        gdf = self.gdf_communes[dept]
        norm_input = self._normalize_name(commune_name)

        for _, row in gdf.iterrows():
            nom_geojson = row.get('nom', '').strip()
            norm_geojson = self._normalize_name(nom_geojson)

            if norm_input == norm_geojson:
                return True

        return False

    def get_corrections(self) -> List[Dict]:
        """Obtenir toutes les corrections appliquées"""
        return self.corrections

    def reset(self):
        """Réinitialiser pour nouveau GPX"""
        self.current_step = 0
        self.corrections = []
