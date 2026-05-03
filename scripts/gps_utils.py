#!/usr/bin/env python3
"""Utilitaires GPS et géométrie"""

from math import radians, cos, sin, asin, sqrt

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculer distance entre 2 points GPS en mètres (formule haversine)
    
    Args:
        lat1, lon1: Latitude/Longitude point 1 (degrés)
        lat2, lon2: Latitude/Longitude point 2 (degrés)
    
    Returns:
        Distance en mètres
    """
    # Rayon terrestre en mètres
    R = 6371000
    
    # Convertir en radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Différences
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Formule haversine
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    return R * c

def sample_points(points: list, distance_m: int = 500) -> list:
    """
    Échantillonner les points GPS : garder 1 point tous les X mètres
    
    Args:
        points: Liste de tuples (lat, lon)
        distance_m: Distance minimale entre points (défaut 500m)
    
    Returns:
        Liste filtrée des points
    """
    if not points or len(points) < 2:
        return points
    
    sampled = [points[0]]  # Garder le premier point
    last_lat, last_lon = points[0]
    
    for lat, lon in points[1:]:
        dist = haversine(last_lat, last_lon, lat, lon)
        
        # Si on a parcouru au moins distance_m, garder ce point
        if dist >= distance_m:
            sampled.append((lat, lon))
            last_lat, last_lon = lat, lon
    
    # Toujours garder le dernier point
    if points[-1] not in sampled:
        sampled.append(points[-1])
    
    return sampled