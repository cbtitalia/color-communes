#!/usr/bin/env python3
"""Service SQLite pour accumulation cumulative des communes"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service de gestion base SQLite pour historique communes"""

    def __init__(self, db_path: str = "/data/color_communes.db"):
        """
        Initialiser le service et créer schéma si nécessaire

        Args:
            db_path: Chemin vers fichier SQLite
        """
        self.db_path = db_path
        self.connection = None

        try:
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row
            self._init_schema()
            logger.info(f"Database initialized: {db_path}")
        except Exception as e:
            logger.error(f"Erreur initialisation DB: {e}")
            raise

    def _init_schema(self):
        """Créer schéma si tables n'existent pas"""
        cursor = self.connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communes (
                id INTEGER PRIMARY KEY,
                commune TEXT NOT NULL UNIQUE,
                insee TEXT NOT NULL,
                dept TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                first_visit TEXT,
                last_visit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_commune ON communes(commune)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dept ON communes(dept)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY,
                file_hash TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                nb_communes INTEGER DEFAULT 0,
                nb_depts INTEGER DEFAULT 0,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON processed_files(file_hash)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                color_palette TEXT DEFAULT 'classic',
                map_size TEXT DEFAULT 'medium',
                show_stats INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON user_preferences(user_id)")

        self.connection.commit()
        logger.info("Schema initialized")

    def upsert_communes(self, communes: Dict) -> bool:
        """
        Insérer ou mettre à jour communes après traitement GPX

        Args:
            communes: Dict from nominatim.batch_geocode() avec nom commune comme clé
                     {commune_name: {commune, dept, insee, count, ...}}

        Returns:
            True si succès, False sinon
        """
        if not communes:
            logger.warning("Aucune commune à insérer")
            return False

        try:
            cursor = self.connection.cursor()
            now = datetime.now().isoformat()

            for commune_name, data in communes.items():
                commune = data.get('commune', commune_name)
                insee = data.get('insee')
                dept = data.get('dept')
                count = data.get('count', 1)

                cursor.execute("""
                    INSERT INTO communes (commune, insee, dept, count, first_visit, last_visit, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(commune) DO UPDATE SET
                        count = count + ?,
                        last_visit = ?,
                        updated_at = ?
                """, (commune, insee, dept, count, now, now, now, now, count, now, now))

            self.connection.commit()
            logger.info(f"Upserted {len(communes)} communes")
            return True

        except Exception as e:
            logger.error(f"Erreur upsert communes: {e}")
            return False

    def get_all_communes(self) -> Optional[Dict]:
        """
        Récupérer toutes les communes pour /cumul

        Returns:
            Dict {commune_name: {insee, dept, count, ...}} ou None si erreur
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM communes ORDER BY commune")
            rows = cursor.fetchall()

            communes = {}
            for row in rows:
                communes[row['commune']] = {
                    'commune': row['commune'],
                    'insee': row['insee'],
                    'dept': row['dept'],
                    'count': row['count'],
                    'first_visit': row['first_visit'],
                    'last_visit': row['last_visit'],
                }

            logger.info(f"Retrieved {len(communes)} communes from DB")
            return communes

        except Exception as e:
            logger.error(f"Erreur lecture communes: {e}")
            return None

    def get_stats(self) -> Optional[Dict]:
        """
        Calculer statistiques pour /stats

        Returns:
            Dict avec total_communes, total_depts, total_passages, first_visit, last_visit, top_communes
        """
        try:
            cursor = self.connection.cursor()

            # Total communes
            cursor.execute("SELECT COUNT(*) as total FROM communes")
            total_communes = cursor.fetchone()['total']

            # Total départements
            cursor.execute("SELECT COUNT(DISTINCT dept) as total FROM communes")
            total_depts = cursor.fetchone()['total']

            # Total passages (somme des counts)
            cursor.execute("SELECT SUM(count) as total FROM communes")
            total_passages = cursor.fetchone()['total'] or 0

            # Dates
            cursor.execute("SELECT MIN(first_visit) as first, MAX(last_visit) as last FROM communes")
            dates = cursor.fetchone()
            first_visit = dates['first'] or "N/A"
            last_visit = dates['last'] or "N/A"

            # Top communes (5 avec plus de passages)
            cursor.execute("""
                SELECT commune, count FROM communes
                ORDER BY count DESC, commune ASC
                LIMIT 5
            """)
            top_communes = [(row['commune'], row['count']) for row in cursor.fetchall()]

            return {
                'total_communes': total_communes,
                'total_depts': total_depts,
                'total_passages': total_passages,
                'first_visit': first_visit,
                'last_visit': last_visit,
                'top_communes': top_communes,
            }

        except Exception as e:
            logger.error(f"Erreur calcul stats: {e}")
            return None

    def reset_database(self) -> bool:
        """
        Réinitialiser la base (supprimer toutes communes)

        Returns:
            True si succès, False sinon
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM communes")
            self.connection.commit()
            logger.info("Database reset complete")
            return True

        except Exception as e:
            logger.error(f"Erreur reset DB: {e}")
            return False

    def is_file_processed(self, file_hash: str) -> bool:
        """
        Vérifier si un fichier a déjà été traité

        Args:
            file_hash: Hash MD5/SHA256 du fichier

        Returns:
            True si fichier déjà traité, False sinon
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM processed_files WHERE file_hash = ?", (file_hash,))
            result = cursor.fetchone()
            is_processed = result['count'] > 0

            if is_processed:
                logger.info(f"File already processed: {file_hash}")
            return is_processed

        except Exception as e:
            logger.error(f"Erreur vérification fichier: {e}")
            return False

    def register_file(self, file_hash: str, filename: str, nb_communes: int = 0, nb_depts: int = 0) -> bool:
        """
        Enregistrer un fichier comme traité

        Args:
            file_hash: Hash MD5/SHA256 du fichier
            filename: Nom original du fichier
            nb_communes: Nombre de communes trouvées
            nb_depts: Nombre de départements

        Returns:
            True si succès, False sinon
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO processed_files (file_hash, filename, nb_communes, nb_depts)
                VALUES (?, ?, ?, ?)
            """, (file_hash, filename, nb_communes, nb_depts))
            self.connection.commit()
            logger.info(f"File registered: {filename} ({nb_communes} communes, {nb_depts} depts)")
            return True

        except sqlite3.IntegrityError:
            logger.warning(f"File already in database: {file_hash}")
            return True
        except Exception as e:
            logger.error(f"Erreur enregistrement fichier: {e}")
            return False

    def get_gpx_history(self) -> Optional[List[Dict]]:
        """
        Récupérer historique des GPX importés

        Returns:
            Liste de dicts {filename, nb_communes, nb_depts, processed_at}
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT filename, nb_communes, nb_depts, processed_at
                FROM processed_files
                ORDER BY processed_at DESC
            """)

            rows = cursor.fetchall()
            history = []
            for row in rows:
                history.append({
                    'filename': row['filename'],
                    'nb_communes': row['nb_communes'],
                    'nb_depts': row['nb_depts'],
                    'processed_at': row['processed_at'],
                })

            logger.info(f"Retrieved {len(history)} GPX history entries")
            return history

        except Exception as e:
            logger.error(f"Erreur lecture historique GPX: {e}")
            return None

    def get_communes_by_date(self, from_date: str) -> Optional[Dict]:
        """
        Récupérer communes visitées depuis une date donnée

        Args:
            from_date: Date ISO format (YYYY-MM-DD)

        Returns:
            Dict {commune_name: {commune, insee, dept, count, first_visit, last_visit}}
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM communes
                WHERE first_visit >= ?
                ORDER BY commune
            """, (from_date,))

            rows = cursor.fetchall()
            communes = {}
            for row in rows:
                communes[row['commune']] = {
                    'commune': row['commune'],
                    'insee': row['insee'],
                    'dept': row['dept'],
                    'count': row['count'],
                    'first_visit': row['first_visit'],
                    'last_visit': row['last_visit'],
                }

            logger.info(f"Retrieved {len(communes)} communes from {from_date}")
            return communes

        except Exception as e:
            logger.error(f"Erreur date range query: {e}")
            return None

    def get_communes_from_gpx(self, gpx_filename: str) -> List[Dict]:
        """Récupérer communes associées à un GPX"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT DISTINCT name, postcode, dept
                FROM communes
                WHERE source_file = ?
                ORDER BY dept, name
            """, (gpx_filename,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Erreur get_communes_from_gpx: {e}")
            return []

    def apply_validation_correction(self, gpx_filename: str, correction: Dict):
        """Appliquer une correction de validation commune"""
        try:
            cursor = self.connection.cursor()

            if correction['type'] == 'duplicate_resolved':
                # Supprimer doublon, garder le code postal choisi
                cursor.execute("""
                    DELETE FROM communes
                    WHERE name = ? AND postcode != ? AND source_file = ?
                """, (correction['commune'], correction['chosen_postcode'], gpx_filename))
                logger.info(f"Doublon résolu: {correction['commune']} → {correction['chosen_postcode']}")

            elif correction['type'] == 'multi_dept':
                # Supprimer autre département
                cursor.execute("""
                    DELETE FROM communes
                    WHERE name = ? AND dept != ? AND source_file = ?
                """, (correction['commune'], correction['chosen_dept'], gpx_filename))
                logger.info(f"Multi-dept résolu: {correction['commune']} → {correction['chosen_dept']}")

            self.connection.commit()

        except Exception as e:
            logger.error(f"Erreur apply_validation_correction: {e}")

    def log_reprocessing(self, gpx_filename: str, corrections: List[Dict]):
        """Enregistrer retraitement après validation"""
        try:
            cursor = self.connection.cursor()

            # Créer table si nécessaire
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gpx_processing_history (
                    id INTEGER PRIMARY KEY,
                    filename TEXT NOT NULL,
                    event TEXT,
                    nb_corrections INTEGER,
                    status TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                INSERT INTO gpx_processing_history
                (filename, event, nb_corrections, status, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (gpx_filename, 'reprocessed_with_corrections', len(corrections), 'completed'))

            self.connection.commit()
            logger.info(f"Reprocessing logged: {gpx_filename} ({len(corrections)} corrections)")

        except Exception as e:
            logger.error(f"Erreur log_reprocessing: {e}")

    def get_communes_in_range(self, start_date: str, end_date: str) -> Optional[Dict]:
        """
        Récupérer communes visitées dans une plage de dates

        Args:
            start_date: Date ISO format (YYYY-MM-DD)
            end_date: Date ISO format (YYYY-MM-DD)

        Returns:
            Dict {commune_name: {...}}
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM communes
                WHERE first_visit BETWEEN ? AND ?
                ORDER BY commune
            """, (start_date, end_date))

            rows = cursor.fetchall()
            communes = {}
            for row in rows:
                communes[row['commune']] = {
                    'commune': row['commune'],
                    'insee': row['insee'],
                    'dept': row['dept'],
                    'count': row['count'],
                    'first_visit': row['first_visit'],
                    'last_visit': row['last_visit'],
                }

            logger.info(f"Retrieved {len(communes)} communes in range {start_date} to {end_date}")
            return communes

        except Exception as e:
            logger.error(f"Erreur range query: {e}")
            return None

    def get_user_preference(self, user_id: int, key: str) -> Optional[str]:
        """
        Récupérer préférence utilisateur

        Args:
            user_id: ID utilisateur Telegram
            key: Clé de préférence (color_palette, map_size, show_stats)

        Returns:
            Valeur de la préférence ou None si non trouvée
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT {key} FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                return row[key]
            return None

        except Exception as e:
            logger.error(f"Erreur lecture préférence: {e}")
            return None

    def set_user_preference(self, user_id: int, key: str, value: str) -> bool:
        """
        Sauvegarder préférence utilisateur

        Args:
            user_id: ID utilisateur Telegram
            key: Clé de préférence
            value: Valeur à sauvegarder

        Returns:
            True si succès, False sinon
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"""
                INSERT INTO user_preferences (user_id, {key})
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    {key} = ?,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, value, value))
            self.connection.commit()
            logger.info(f"Preference saved: user={user_id}, {key}={value}")
            return True

        except Exception as e:
            logger.error(f"Erreur sauvegarde préférence: {e}")
            return False

    def save_commune_correction(self, original_name: str, corrected_name: str) -> bool:
        """Sauvegarder une correction de commune pour réutilisation future"""
        try:
            cursor = self.connection.cursor()

            # Vérifier si correction existe déjà
            cursor.execute(
                "SELECT COUNT(*) as count FROM commune_corrections WHERE original_name = ?",
                (original_name,)
            )
            exists = cursor.fetchone()['count'] > 0

            if exists:
                # Mettre à jour count et date
                cursor.execute("""
                    UPDATE commune_corrections
                    SET applied_count = applied_count + 1, last_applied = CURRENT_TIMESTAMP
                    WHERE original_name = ?
                """, (original_name,))
            else:
                # Créer la table si nécessaire
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS commune_corrections (
                        id INTEGER PRIMARY KEY,
                        original_name TEXT NOT NULL UNIQUE,
                        corrected_name TEXT NOT NULL,
                        applied_count INTEGER DEFAULT 1,
                        last_applied TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Insérer la correction
                cursor.execute("""
                    INSERT INTO commune_corrections (original_name, corrected_name)
                    VALUES (?, ?)
                """, (original_name, corrected_name))

            self.connection.commit()
            logger.info(f"Correction sauvegardée: {original_name} → {corrected_name}")
            return True

        except Exception as e:
            logger.error(f"Erreur sauvegarde correction: {e}")
            return False

    def get_commune_corrections(self) -> Dict:
        """Récupérer toutes les corrections sauvegardées"""
        try:
            cursor = self.connection.cursor()

            # Créer la table si nécessaire
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS commune_corrections (
                    id INTEGER PRIMARY KEY,
                    original_name TEXT NOT NULL UNIQUE,
                    corrected_name TEXT NOT NULL,
                    applied_count INTEGER DEFAULT 1,
                    last_applied TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("SELECT original_name, corrected_name FROM commune_corrections")
            corrections = {}
            for row in cursor.fetchall():
                corrections[row['original_name']] = row['corrected_name']

            logger.info(f"Corrections chargées: {len(corrections)} entrées")
            return corrections

        except Exception as e:
            logger.error(f"Erreur lecture corrections: {e}")
            return {}

    def close(self):
        """Fermer la connexion"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
