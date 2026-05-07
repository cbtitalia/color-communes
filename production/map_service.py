#!/usr/bin/env python3
"""Service cartographie - génération PNG communes colorisées"""

import logging
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.colors import LinearSegmentedColormap
import io
import json
import unicodedata
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class MapService:
    """Service de génération de cartes PNG colorisées"""

    # Palettes de colorisation (4 options)
    PALETTES = {
        'classic': {
            1: '#FFF176',      # Jaune pâle
            2: '#FF8F00',      # Orange
            3: '#E53935',      # Rouge
            4: '#B71C1C',      # Rouge foncé
        },
        'vibrant': {
            1: '#FFEE58',      # Jaune vif
            2: '#FF6F00',      # Orange vif
            3: '#D32F2F',      # Rouge vif
            4: '#880E4F',      # Magenta foncé
        },
        'pastel': {
            1: '#FFE082',      # Jaune pastel
            2: '#FFB74D',      # Orange pastel
            3: '#EF9A9A',      # Rose pastel
            4: '#CE93D8',      # Mauve pastel
        },
        'grayscale': {
            1: '#F5F5F5',      # Gris très clair
            2: '#BDBDBD',      # Gris moyen
            3: '#757575',      # Gris foncé
            4: '#212121',      # Gris très foncé
        },
    }

    def __init__(self, output_dir: str = "/data", corrections_file: str = "/data/commune_corrections.json"):
        """
        Initialiser le service

        Args:
            output_dir: Répertoire pour sauvegarder les PNG
            corrections_file: Fichier JSON avec corrections de noms de communes
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Charger les corrections de noms
        self.corrections = {}
        self.multi_corrections = {}
        corrections_path = Path(corrections_file)
        if corrections_path.exists():
            try:
                with open(corrections_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.corrections = data.get('corrections', {})
                    self.multi_corrections = data.get('multi_corrections', {})
                    logger.info(f"Corrections chargées: {len(self.corrections)} + {len(self.multi_corrections)} multi")
            except Exception as e:
                logger.warning(f"Impossible charger corrections: {e}")

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normaliser le nom pour matching robuste (accents, espaces, tirets)"""
        if not name:
            return ""
        # Supprimer les accents
        name = unicodedata.normalize('NFD', name)
        name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
        # Convertir en minuscules et supprimer espaces/tirets
        name = str(name).lower().replace(' ', '').replace('-', '').replace("'", '')
        return name

    def _get_color(self, nb_passages: int, palette: str = 'classic', commune_name: str = '') -> str:
        """
        Obtenir la couleur selon le nombre de passages et palette

        Args:
            nb_passages: Nombre de passages
            palette: Nom de la palette ('classic', 'vibrant', 'pastel', 'grayscale')
            commune_name: Nom de la commune (pour exceptions)

        Returns:
            Code couleur hex
        """
        # Exception : Belfort toujours en vert
        if commune_name and commune_name.lower() == 'belfort':
            return '#76FF03'  # Vert lime

        colors = self.PALETTES.get(palette, self.PALETTES['classic'])

        if nb_passages >= 10:
            return colors[4]
        elif nb_passages >= 5:
            return colors[3]
        elif nb_passages >= 2:
            return colors[2]
        else:
            return colors[1]

    def _filter_isolated_geometries(self, gdf, max_distance_km: float = 20.0):
        """
        Enlever les polygones isolés (fragmentés) trop loin du centre de masse

        Args:
            gdf: GeoDataFrame
            max_distance_km: Distance max en km (défaut: 20 km pour inclure communes isolées comme Gyromagny)

        Returns:
            GeoDataFrame filtré
        """
        if len(gdf) == 0:
            return gdf

        # Calculer le centroïde moyen
        centroids = gdf.geometry.centroid
        center = centroids.unary_union.centroid

        # Calculer la distance de chaque polygon au centre (en degrés ≈ 111 km par degré)
        gdf['dist_to_center'] = gdf.geometry.centroid.distance(center)

        # Filtrer : garder seulement ceux qui sont près du centre
        gdf_filtered = gdf[gdf['dist_to_center'] <= (max_distance_km / 111.0)].copy()

        # Log les polygones supprimés
        removed = len(gdf) - len(gdf_filtered)
        if removed > 0:
            logger.warning(f"Filtrage: {removed} polygones isolés supprimés (distance > {max_distance_km}km)")

        return gdf_filtered.drop(columns=['dist_to_center'])

    def generate_map(
        self,
        geojsons: Dict[str, Dict],
        communes: Dict[str, Dict],
        title: str = "Ma carte cycliste",
        palette: str = 'classic',
        map_size: str = 'medium',
        show_stats: bool = True
    ) -> tuple:
        """
        Générer une carte PNG colorisée

        Args:
            geojsons: Dict {dept: geojson_dict}
            communes: Dict {commune: {commune, dept, count, ...}}
            title: Titre de la carte
            palette: Palette de couleurs ('classic', 'vibrant', 'pastel', 'grayscale')
            map_size: Taille de la carte ('small' 640, 'medium' 1080, 'large' 1600)
            show_stats: Afficher statistiques sur la carte

        Returns:
            (png_bytes, rapport) ou (None, None) si erreur
        """
        try:
            # Déterminer taille figure selon map_size
            figsize_map = {
                'small': (8, 8),
                'medium': (12, 12),
                'large': (16, 16),
            }
            figsize = figsize_map.get(map_size, (12, 12))

            # Créer figure
            fig, ax = plt.subplots(figsize=figsize, dpi=90)

            # Charger et dessiner tous les GeoJSON (base grise)
            all_bounds = None

            try:
                for dept_num, geojson in geojsons.items():
                    # Filtrer features sans geometry valide
                    valid_features = [f for f in geojson["features"] if f.get("geometry") and f["geometry"].get("type")]
                    if not valid_features:
                        logger.warning(f"Dept {dept_num}: Aucune feature valide")
                        continue
                    gdf = gpd.GeoDataFrame.from_features(valid_features)

                    # Ajouter colonne 'color' (défaut blanc pour communes non visitées)
                    gdf['color'] = '#FFFFFF'
                    gdf['visited'] = False

                    logger.info(f"Dept {dept_num}: {len(gdf)} communes dans GeoJSON")

                    # Coloriser communes visitées (par nom normalisé)
                    for idx, row in gdf.iterrows():
                        nom_geojson = str(row.get('nom') or row.get('name') or '').strip()
                        nom_norm = self._normalize_name(nom_geojson)

                        # Chercher exact d'abord
                        if nom_geojson in communes:
                            gdf.loc[idx, 'color'] = self._get_color(communes[nom_geojson]['count'], palette, nom_geojson)
                            gdf.loc[idx, 'visited'] = True
                            logger.info(f"✓ Match exact: {nom_geojson} (count={communes[nom_geojson]['count']})")
                        else:
                            # Chercher par nom normalisé
                            for comm_name, comm_data in communes.items():
                                if self._normalize_name(comm_name) == nom_norm:
                                    gdf.loc[idx, 'color'] = self._get_color(comm_data['count'], palette, nom_geojson)
                                    gdf.loc[idx, 'visited'] = True
                                    logger.info(f"✓ Match norm: {nom_geojson} ≈ {comm_name} (count={comm_data['count']})")
                                    break
                            else:
                                # Chercher avec corrections (typos/variations)
                                if nom_geojson in self.corrections:
                                    corrected_name = self.corrections[nom_geojson]
                                    if corrected_name in communes:
                                        gdf.loc[idx, 'color'] = self._get_color(communes[corrected_name]['count'], palette, nom_geojson)
                                        gdf.loc[idx, 'visited'] = True
                                        logger.info(f"✓ Match correction: {nom_geojson} → {corrected_name} (count={communes[corrected_name]['count']})")
                                    else:
                                        logger.debug(f"✗ Correction appliquée mais pas trouvée: {nom_geojson} → {corrected_name}")
                                else:
                                    logger.debug(f"✗ Pas de match: {nom_geojson}")

                    # Dessiner les communes
                    gdf.plot(ax=ax, color=gdf['color'], edgecolor='#333333', linewidth=0.2, zorder=5)

                    # Accentuer contour département (limite extérieure) - après plot
                    try:
                        from shapely.geometry import LineString, MultiLineString
                        # Filtrer seulement les Polygons pour boundary (Points n'en ont pas)
                        gdf_polygons = gdf[gdf.geometry.type == 'Polygon']
                        if len(gdf_polygons) > 0:
                            dept_boundary = gdf_polygons.unary_union.boundary
                        else:
                            dept_boundary = None

                        if dept_boundary and not dept_boundary.is_empty:
                            if isinstance(dept_boundary, LineString):
                                logger.info(f"Dept {dept_num}: boundary type={type(dept_boundary).__name__}, has_coords={len(dept_boundary.coords)}")
                                if len(dept_boundary.coords) > 0:
                                    x, y = dept_boundary.xy
                                    ax.plot(x, y, color='#1a1a1a', linewidth=3.0, zorder=100, solid_capstyle='round')
                                    logger.info(f"Dept {dept_num}: plotted single LineString with {len(x)} points")
                            elif isinstance(dept_boundary, MultiLineString):
                                logger.info(f"Dept {dept_num}: boundary type=MultiLineString, parts={len(dept_boundary.geoms)}")
                                for i, geom in enumerate(dept_boundary.geoms):
                                    if len(geom.coords) > 0:
                                        x, y = geom.xy
                                        ax.plot(x, y, color='#1a1a1a', linewidth=3.0, zorder=100, solid_capstyle='round')
                                        logger.info(f"Dept {dept_num}: plotted MultiLineString[{i}] with {len(x)} points")
                            else:
                                logger.warning(f"Dept {dept_num}: boundary is {type(dept_boundary).__name__}, not LineString/MultiLineString")
                        else:
                            logger.debug(f"Dept {dept_num}: boundary is empty or None")
                    except Exception as e:
                        logger.error(f"Erreur accentuation département {dept_num}: {e}", exc_info=True)

                    # Garder les bounds
                    if all_bounds is None:
                        all_bounds = gdf.total_bounds
                    else:
                        bounds = gdf.total_bounds
                        all_bounds = [
                            min(all_bounds[0], bounds[0]),
                            min(all_bounds[1], bounds[1]),
                            max(all_bounds[2], bounds[2]),
                            max(all_bounds[3], bounds[3]),
                        ]

            except Exception as e:
                logger.warning(f"Dept {dept_num}: skip - {e}")
            # Mettre en forme
            ax.set_xlim(all_bounds[0], all_bounds[2])
            ax.set_ylim(all_bounds[1], all_bounds[3])
            ax.set_aspect('equal')
            ax.axis('off')

            # Ajouter titre
            fig.suptitle(title, fontsize=20, fontweight='bold', y=0.98)

            # Légende colorisation (utiliser couleurs de la palette)
            colors = self.PALETTES.get(palette, self.PALETTES['classic'])
            legend_elements = [
                Patch(facecolor=colors[1], edgecolor='#333333', label='1 passage'),
                Patch(facecolor=colors[2], edgecolor='#333333', label='2-4 passages'),
                Patch(facecolor=colors[3], edgecolor='#333333', label='5-9 passages'),
                Patch(facecolor=colors[4], edgecolor='#333333', label='10+ passages'),
                Patch(facecolor='#FFFFFF', edgecolor='#333333', label='Non visitée'),
            ]
            ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

            # Ajouter statistiques (si show_stats=True)
            if show_stats:
                stats_text = f"🚴 {len(communes)} communes | 📍 {len(geojsons)} départements"
                fig.text(0.5, 0.01, stats_text, ha='center', fontsize=12)

            # Rapport communes non reconnues
            communes_nominatim = set(communes.keys())
            non_colorisees = []
            try:
                for dept_num, geojson in geojsons.items():
                    # Filtrer features sans geometry valide
                    valid_features = [f for f in geojson["features"] if f.get("geometry") and f["geometry"].get("type")]
                    if not valid_features:
                        logger.warning(f"Dept {dept_num}: Aucune feature valide")
                        continue
                    gdf_temp = gpd.GeoDataFrame.from_features(valid_features)
                    for nom in gdf_temp['nom'].unique():
                        if nom not in communes_nominatim:
                            proches = [c for c in communes_nominatim if c.lower() in str(nom).lower() or str(nom).lower() in c.lower()]
                            non_colorisees.append((nom, proches))

            except Exception as e:
                logger.warning(f"Dept {dept_num}: skip - {e}")
            # Rapport communes non colorisées
            rapport = ""
            if non_colorisees:
                rapport = f"⚠️ Communes du GeoJSON non reconnues:\n"
                for nom, proches in non_colorisees[:5]:
                    if proches:
                        # Marquer celles qui sont dans le GPX
                        proches_in_gpx = [c for c in proches if c in communes]
                        if proches_in_gpx:
                            rapport += f"  ≈ {str(nom) if nom else '?'} → {', '.join(proches_in_gpx)} ✓\n"
                        else:
                            rapport += f"  ✗ {str(nom) if nom else '?'} → {', '.join(str(p) for p in proches[:2])}\n"
                    else:
                        rapport += f"  ✗ {str(nom) if nom else '?'}\n"
                        logger.warning(f"  ✗ {str(nom) if nom else '?'} → aucune correspondance")

            # Exporter PNG en bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
            buf.seek(0)
            png_bytes = buf.getvalue()

            plt.close(fig)

            logger.info(f"Carte générée: {len(png_bytes)} bytes")
            return (png_bytes, rapport)

        except Exception as e:
            logger.error(f"Erreur génération carte: {e}")
            return (None, "")

    def generate_comparison_map(
        self,
        geojsons: Dict[str, Dict],
        communes_before: Dict[str, Dict],
        communes_after: Dict[str, Dict],
        palette: str = 'classic'
    ) -> tuple:
        """
        Générer deux cartes côte-à-côte (avant/après) pour comparaison

        Args:
            geojsons: Dict {dept: geojson_dict}
            communes_before: Communes visitées avant la date pivot
            communes_after: Communes visitées après la date pivot
            palette: Palette de couleurs

        Returns:
            (png_bytes, rapport) ou (None, None) si erreur
        """
        try:
            # Créer figure avec 2 sous-graphiques
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10), dpi=90)

            all_bounds = None

            for ax, communes, title_suffix in [(ax1, communes_before, "AVANT"),
                                                (ax2, communes_after, "APRÈS")]:
                # Dessiner toutes les communes
                try:
                    for dept_num, geojson in geojsons.items():
                        # Filtrer features sans geometry valide
                        valid_features = [f for f in geojson["features"] if f.get("geometry") and f["geometry"].get("type")]
                        if not valid_features:
                            logger.warning(f"Dept {dept_num}: Aucune feature valide")
                            continue
                        gdf = gpd.GeoDataFrame.from_features(valid_features)

                        gdf['color'] = '#FFFFFF'
                        gdf['visited'] = False

                        # Coloriser communes visitées
                        for idx, row in gdf.iterrows():
                            nom_geojson = str(row.get('nom') or row.get('name') or '').strip()
                            nom_norm = self._normalize_name(nom_geojson)

                            if nom_geojson in communes:
                                gdf.loc[idx, 'color'] = self._get_color(communes[nom_geojson]['count'], palette)
                                gdf.loc[idx, 'visited'] = True
                            else:
                                for comm_name, comm_data in communes.items():
                                    if self._normalize_name(comm_name) == nom_norm:
                                        gdf.loc[idx, 'color'] = self._get_color(comm_data['count'], palette)
                                        gdf.loc[idx, 'visited'] = True
                                        break

                        gdf.plot(ax=ax, color=gdf['color'], edgecolor='#333333', linewidth=0.2, zorder=5)

                        # Accentuer contour département
                        try:
                            from shapely.geometry import LineString, MultiLineString
                            dept_boundary = gdf.unary_union.boundary
                            if dept_boundary and not dept_boundary.is_empty:
                                if isinstance(dept_boundary, LineString):
                                    if len(dept_boundary.coords) > 0:
                                        x, y = dept_boundary.xy
                                        ax.plot(x, y, color='#1a1a1a', linewidth=3.0, zorder=100, solid_capstyle='round')
                                elif isinstance(dept_boundary, MultiLineString):
                                    for geom in dept_boundary.geoms:
                                        if len(geom.coords) > 0:
                                            x, y = geom.xy
                                            ax.plot(x, y, color='#1a1a1a', linewidth=3.0, zorder=100, solid_capstyle='round')
                        except Exception as e:
                            logger.debug(f"Erreur accentuation département: {e}")

                        # Garder les bounds
                        if all_bounds is None:
                            all_bounds = gdf.total_bounds
                        else:
                            bounds = gdf.total_bounds
                            all_bounds = [
                                min(all_bounds[0], bounds[0]),
                                min(all_bounds[1], bounds[1]),
                                max(all_bounds[2], bounds[2]),
                                max(all_bounds[3], bounds[3]),
                            ]

                except Exception as e:
                    logger.warning(f"Dept {dept_num}: skip - {e}")
                # Mettre en forme
                ax.set_xlim(all_bounds[0], all_bounds[2])
                ax.set_ylim(all_bounds[1], all_bounds[3])
                ax.set_aspect('equal')
                ax.axis('off')
                ax.set_title(title_suffix, fontsize=16, fontweight='bold')

                # Légende pour le côté "avant" uniquement
                if ax == ax1:
                    colors = self.PALETTES.get(palette, self.PALETTES['classic'])
                    legend_elements = [
                        Patch(facecolor=colors[1], edgecolor='#333333', label='1 passage'),
                        Patch(facecolor=colors[2], edgecolor='#333333', label='2-4 passages'),
                        Patch(facecolor=colors[3], edgecolor='#333333', label='5-9 passages'),
                        Patch(facecolor=colors[4], edgecolor='#333333', label='10+ passages'),
                        Patch(facecolor='#FFFFFF', edgecolor='#333333', label='Non visitée'),
                    ]
                    ax.legend(handles=legend_elements, loc='lower left', fontsize=9)

            fig.suptitle("Comparaison avant | après", fontsize=18, fontweight='bold', y=0.98)

            # Exporter PNG
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
            buf.seek(0)
            png_bytes = buf.getvalue()

            plt.close(fig)

            logger.info(f"Cartes comparaison générées: {len(communes_before)} avant, {len(communes_after)} après")
            return (png_bytes, "")

        except Exception as e:
            logger.error(f"Erreur génération carte comparaison: {e}")
            return (None, "")

    def save_png(self, png_bytes: bytes, filename: str) -> Optional[Path]:
        """
        Sauvegarder PNG sur disque

        Args:
            png_bytes: Contenu PNG
            filename: Nom fichier (ex: "sortie_2026-04-29.png")

        Returns:
            Chemin fichier ou None si erreur
        """
        try:
            filepath = self.output_dir / filename
            with open(filepath, 'wb') as f:
                f.write(png_bytes)
            logger.info(f"PNG sauvegardé: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Erreur sauvegarde PNG: {e}")
            return None
