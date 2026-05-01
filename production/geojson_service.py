#!/usr/bin/env python3
"""Service GeoJSON - téléchargement et cache communes"""

import logging
import requests
import json
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class GeoJsonService:
    """Service de gestion GeoJSON avec cache local"""

    BASE_URL = "https://france-geojson.gregoiredavid.fr/repo/departements"

    # Mapping département complet: num -> (num, nom_slug)
    DEPARTMENTS = {
        '01': ('01', 'Ain'),
        '02': ('02', 'Aisne'),
        '03': ('03', 'Allier'),
        '04': ('04', 'Alpes-de-Haute-Provence'),
        '05': ('05', 'Hautes-Alpes'),
        '06': ('06', 'Alpes-Maritimes'),
        '07': ('07', 'Ardèche'),
        '08': ('08', 'Ardennes'),
        '09': ('09', 'Ariège'),
        '10': ('10', 'Aube'),
        '11': ('11', 'Aude'),
        '12': ('12', 'Aveyron'),
        '13': ('13', 'Bouches-du-Rhône'),
        '14': ('14', 'Calvados'),
        '15': ('15', 'Cantal'),
        '16': ('16', 'Charente'),
        '17': ('17', 'Charente-Maritime'),
        '18': ('18', 'Cher'),
        '19': ('19', 'Corrèze'),
        '2A': ('2A', 'Corse-du-Sud'),
        '2B': ('2B', 'Haute-Corse'),
        '21': ('21', 'Côte-d\'Or'),
        '22': ('22', 'Côtes-d\'Armor'),
        '23': ('23', 'Creuse'),
        '24': ('24', 'Dordogne'),
        '25': ('25', 'Doubs'),
        '26': ('26', 'Drôme'),
        '27': ('27', 'Eure'),
        '28': ('28', 'Eure-et-Loir'),
        '29': ('29', 'Finistère'),
        '30': ('30', 'Gard'),
        '31': ('31', 'Haute-Garonne'),
        '32': ('32', 'Gers'),
        '33': ('33', 'Gironde'),
        '34': ('34', 'Hérault'),
        '35': ('35', 'Ille-et-Vilaine'),
        '36': ('36', 'Indre'),
        '37': ('37', 'Indre-et-Loire'),
        '38': ('38', 'Isère'),
        '39': ('39', 'Jura'),
        '40': ('40', 'Landes'),
        '41': ('41', 'Loir-et-Cher'),
        '42': ('42', 'Loire'),
        '43': ('43', 'Haute-Loire'),
        '44': ('44', 'Loire-Atlantique'),
        '45': ('45', 'Loiret'),
        '46': ('46', 'Lot'),
        '47': ('47', 'Lot-et-Garonne'),
        '48': ('48', 'Lozère'),
        '49': ('49', 'Maine-et-Loire'),
        '50': ('50', 'Manche'),
        '51': ('51', 'Marne'),
        '52': ('52', 'Haute-Marne'),
        '53': ('53', 'Mayenne'),
        '54': ('54', 'Meurthe-et-Moselle'),
        '55': ('55', 'Meuse'),
        '56': ('56', 'Morbihan'),
        '57': ('57', 'Moselle'),
        '58': ('58', 'Nièvre'),
        '59': ('59', 'Nord'),
        '60': ('60', 'Oise'),
        '61': ('61', 'Orne'),
        '62': ('62', 'Pas-de-Calais'),
        '63': ('63', 'Puy-de-Dôme'),
        '64': ('64', 'Pyrénées-Atlantiques'),
        '65': ('65', 'Hautes-Pyrénées'),
        '66': ('66', 'Pyrénées-Orientales'),
        '67': ('67', 'Bas-Rhin'),
        '68': ('68', 'Haut-Rhin'),
        '69': ('69', 'Rhône'),
        '70': ('70', 'Haute-Saône'),
        '71': ('71', 'Saône-et-Loire'),
        '72': ('72', 'Sarthe'),
        '73': ('73', 'Savoie'),
        '74': ('74', 'Haute-Savoie'),
        '75': ('75', 'Paris'),
        '76': ('76', 'Seine-Maritime'),
        '77': ('77', 'Seine-et-Marne'),
        '78': ('78', 'Yvelines'),
        '79': ('79', 'Deux-Sèvres'),
        '80': ('80', 'Somme'),
        '81': ('81', 'Tarn'),
        '82': ('82', 'Tarn-et-Garonne'),
        '83': ('83', 'Var'),
        '84': ('84', 'Vaucluse'),
        '85': ('85', 'Vendée'),
        '86': ('86', 'Vienne'),
        '87': ('87', 'Haute-Vienne'),
        '88': ('88', 'Vosges'),
        '89': ('89', 'Yonne'),
        '90': ('90', 'Territoire-de-Belfort'),
        '91': ('91', 'Essonne'),
        '92': ('92', 'Hauts-de-Seine'),
        '93': ('93', 'Seine-Saint-Denis'),
        '94': ('94', 'Val-de-Marne'),
        '95': ('95', 'Val-d\'Oise'),
        '971': ('971', 'Guadeloupe'),
        '972': ('972', 'Martinique'),
        '973': ('973', 'Guyane'),
        '974': ('974', 'Réunion'),
        '976': ('976', 'Mayotte'),
    }

    def __init__(self, cache_dir: str = "/data/geojson_cache"):
        """
        Initialiser le service

        Args:
            cache_dir: Répertoire pour stocker le cache
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache GeoJSON: {self.cache_dir}")

    def _get_cache_path(self, dept_num: str) -> Path:
        """Chemin du fichier cache pour un département"""
        return self.cache_dir / f"communes-{dept_num}.geojson"

    def download_geojson(self, dept_num: str) -> Optional[Dict]:
        """
        Télécharger le GeoJSON d'un département (avec cache)

        Args:
            dept_num: Numéro département (ex: '75', '90')

        Returns:
            Dict GeoJSON ou None si erreur
        """
        cache_path = self._get_cache_path(dept_num)

        # Vérifier le cache
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    logger.info(f"GeoJSON dept {dept_num} depuis cache")
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erreur lecture cache {dept_num}: {e}")

        # Télécharger
        try:
            # Construire l'URL avec le bon format
            dept_info = self.DEPARTMENTS.get(dept_num)
            if not dept_info:
                logger.warning(f"Département {dept_num} non trouvé")
                return None

            dept_num_clean, dept_name = dept_info
            # Format requis par l'API: 25-doubs (minuscules, accents remplacés)
            dept_name_slug = (dept_name.lower()
                             .replace(' ', '-')
                             .replace('é', 'e')
                             .replace('è', 'e')
                             .replace('ê', 'e')
                             .replace('ô', 'o')
                             .replace('à', 'a')
                             .replace('ç', 'c')
                             .replace("'", '-'))
            url = f"{self.BASE_URL}/{dept_num_clean}-{dept_name_slug}/communes-{dept_num_clean}-{dept_name_slug}.geojson"

            logger.info(f"Téléchargement GeoJSON dept {dept_num} depuis {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            geojson = response.json()

            # Sauvegarder en cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(geojson, f)

            logger.info(f"GeoJSON dept {dept_num} mis en cache")
            return geojson

        except requests.RequestException as e:
            logger.error(f"Erreur téléchargement GeoJSON {dept_num}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur parsing GeoJSON {dept_num}: {e}")
            return None

    def get_geojson_for_communes(self, communes: Dict) -> Dict[str, Dict]:
        """
        Télécharger les GeoJSON pour tous les départements des communes

        Args:
            communes: Dict {insee: {commune, dept, count}}

        Returns:
            Dict {dept_num: geojson}
        """
        depts = sorted(set(c['dept'] for c in communes.values()))
        geojsons = {}

        for dept in depts:
            geojson = self.download_geojson(dept)
            if geojson:
                geojsons[dept] = geojson
            else:
                logger.warning(f"GeoJSON manquant pour dept {dept}")

        logger.info(f"GeoJSON chargés: {len(geojsons)}/{len(depts)} départements")
        return geojsons

    def clear_cache(self):
        """Vider le cache GeoJSON"""
        import shutil
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Cache GeoJSON vidé")
