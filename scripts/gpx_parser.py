#!/usr/bin/env python3
"""Parser GPX - extraction des points GPS"""

import logging
import gpxpy
from io import BytesIO
from typing import Optional
from gps_utils import sample_points

logger = logging.getLogger(__name__)

class GpxParser:
    """Parser de fichiers GPX"""
    
    def __init__(self, sample_distance_m: int = 500):
        """
        Initialiser le parser
        
        Args:
            sample_distance_m: Distance d'échantillonnage en mètres
        """
        self.sample_distance_m = sample_distance_m
    
    def parse(self, gpx_data: bytes) -> Optional[dict]:
        """
        Parser un fichier GPX

        Args:
            gpx_data: Contenu du fichier GPX (bytes)

        Returns:
            Dict avec:
              - points: liste de (lat, lon)
              - sampled_points: points échantillonnés
              - metadata: nom, description, date_start, date_end
              - nb_points: nombre total de points
              - nb_sampled: nombre de points après échantillonnage
        """
        try:
            # Parser le GPX
            gpx = gpxpy.parse(BytesIO(gpx_data))

            # Extraire tous les points
            points = []
            timestamps = []

            # Points des tracks
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        points.append((point.latitude, point.longitude))
                        if point.time:
                            timestamps.append(point.time)
            
            # Points des waypoints
            for waypoint in gpx.waypoints:
                points.append((waypoint.latitude, waypoint.longitude))
            
            if not points:
                logger.warning("Aucun point trouvé dans le GPX")
                return None
            
            # Échantillonner
            sampled = sample_points(points, self.sample_distance_m)

            # Extraire dates (si disponibles)
            date_start = None
            date_end = None
            if timestamps:
                timestamps.sort()
                date_start = timestamps[0].strftime('%Y-%m-%d')
                date_end = timestamps[-1].strftime('%Y-%m-%d')

            logger.info(f"GPX parsé: {len(points)} points → {len(sampled)} échantillonnés")
            if date_start:
                logger.info(f"Dates: {date_start} à {date_end}")

            return {
                'points': points,
                'sampled_points': sampled,
                'nb_points': len(points),
                'nb_sampled': len(sampled),
                'metadata': {
                    'name': gpx.name,
                    'description': gpx.description,
                    'date_start': date_start,
                    'date_end': date_end,
                }
            }
        
        except Exception as e:
            logger.error(f"Erreur parsing GPX: {e}")
            return None