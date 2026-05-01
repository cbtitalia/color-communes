#!/usr/bin/env python3
"""Service reverse geocoding Nominatim - extraction communes"""

import logging
import requests
import time
from typing import Optional, List, Dict
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class NominatimService:
    """Service de reverse geocoding avec Nominatim"""
    
    BASE_URL = "https://nominatim.openstreetmap.org/reverse"
    
    def __init__(self, email: str = "contact@example.com", rate_limit_s: float = 1.0):
        """
        Initialiser le service
        
        Args:
            email: Email pour respecter les conditions Nominatim
            rate_limit_s: Délai minimum entre requêtes (défaut 1s)
        """
        self.email = email
        self.rate_limit_s = rate_limit_s
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'ColorCommunes/1.0 ({email})'
        })
    
    def _wait_for_rate_limit(self):
        """Respecter le rate limit Nominatim (1 req/sec)"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_s:
            time.sleep(self.rate_limit_s - elapsed)
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Faire un reverse geocoding pour un point GPS
        
        Args:
            lat, lon: Latitude/Longitude
        
        Returns:
            Dict avec:
              - insee: Code INSEE commune
              - commune: Nom commune
              - dept: Numéro département
              ou None si erreur
        """
        try:
            self._wait_for_rate_limit()
            
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1,
                'email': self.email,
            }
            
            url = f"{self.BASE_URL}?{urlencode(params)}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            self.last_request_time = time.time()
            data = response.json()

            # Extraire INSEE et commune depuis address
            address = data.get('address', {})
            logger.info(f"Nominatim response: address keys = {list(address.keys())}")

            # Code INSEE depuis le postcode (format XXXXX)
            insee = address.get('postcode', '')
            if insee and len(insee) >= 5:
                insee = insee[:5]
            else:
                insee = None
            
            # Nom commune et type — priorité: hamlet > village > municipality
            # (hamlet/village sont plus spécifiques que municipality qui peut être la ville principale)
            place_type = None
            commune = None

            if address.get('hamlet'):
                commune = address['hamlet']
                place_type = 'hamlet'
            elif address.get('village'):
                commune = address['village']
                place_type = 'village'
            elif address.get('municipality'):
                commune = address['municipality']
                place_type = 'municipality'
            else:
                commune = data.get('name', 'Inconnue')
                place_type = 'unknown'

            logger.info(f"({lat:.2f},{lon:.2f}) → {commune} ({place_type})")

            # Département (2 premiers caractères INSEE)
            dept = insee[:2] if insee else None

            if not insee or not commune:
                logger.warning(f"Données incomplètes pour ({lat}, {lon}): insee={insee}, commune={commune}")
                return None

            logger.debug(f"Nominatim result: insee={insee}, commune={commune}, type={place_type}, postcode={address.get('postcode')}")

            return {
                'insee': insee,
                'commune': commune,
                'dept': dept,
                'type': place_type,
                'lat': lat,
                'lon': lon,
            }
        
        except requests.RequestException as e:
            logger.error(f"Erreur Nominatim ({lat}, {lon}): {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur parsing Nominatim: {e}")
            return None
    
    def batch_geocode(self, points: List[tuple]) -> Dict[str, Dict]:
        """
        Geocoder une liste de points et dédupliquer par commune

        Args:
            points: Liste de (lat, lon)

        Returns:
            Dict {commune_name: {commune, dept, insee, count}}
        """
        communes = {}
        not_found_count = 0

        for lat, lon in points:
            result = self.reverse_geocode(lat, lon)

            if result:
                commune_name = result['commune']

                if commune_name not in communes:
                    communes[commune_name] = {
                        'commune': result['commune'],
                        'dept': result['dept'],
                        'insee': result['insee'],
                        'type': result.get('type', 'unknown'),
                        'count': 0,
                        'first_point': (lat, lon),
                    }

                communes[commune_name]['count'] += 1
            else:
                not_found_count += 1
                logger.warning(f"Point GPS ({lat:.2f},{lon:.2f}) — Aucune commune trouvée")

        logger.info(f"Geocoding complété: {len(communes)} communes uniques, {not_found_count} points non trouvés")
        for name, data in communes.items():
            logger.info(f"  - {name} (INSEE={data['insee']}, dept={data['dept']}, count={data['count']})")
        return communes