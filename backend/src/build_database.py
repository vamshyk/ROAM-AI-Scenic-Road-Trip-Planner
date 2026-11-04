
"""
ROAM - Karnataka SQLite Database Builder

Builds the local SQLite database using:
1. Existing processed OSM CSV files
2. Existing Karnataka OSM PBF file for settlements

The original database is replaced only after the new database
has been successfully built and validated.
"""

import csv
import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_PBF = DATA_DIR / "raw" / "karnataka-latest.osm.pbf"

DATABASE_PATH = DATA_DIR / "karnataka.db"
TEMP_DATABASE_PATH = DATA_DIR / "karnataka_building.db"

BATCH_SIZE = 5000


# ---------------------------------------------------------
# CATEGORY MAPPING
# ---------------------------------------------------------

AMENITY_MAPPING = {
    "restaurant": "food",
    "cafe": "food",
    "fast_food": "food",
    "fuel": "fuel",
    "toilets": "toilets",
    "drinking_water": "drinking_water",
    "parking": "parking",
}

TOURISM_MAPPING = {
    "viewpoint": "viewpoint",
    "attraction": "attraction",
    "museum": "museum",
    "picnic_site": "picnic_site",
    "zoo": "zoo",
    "theme_park": "theme_park",
    "camp_site": "camp_site",
    "information": "information",
}

SETTLEMENT_TYPES = {
    "city",
    "town",
    "village",
    "hamlet",
}


# ---------------------------------------------------------
# DATABASE SCHEMA
# ---------------------------------------------------------

def create_tables(connection):
    cursor = connection.cursor()

    cursor.executescript("""
        CREATE TABLE geo_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            osm_id TEXT,
            feature_type TEXT NOT NULL,
            name TEXT,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        );

        CREATE TABLE pois (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            osm_id TEXT,
            poi_type TEXT NOT NULL,
            name TEXT,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        );

        CREATE TABLE settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            osm_id TEXT,
            name TEXT NOT NULL,
            place_type TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            population INTEGER
        );
    """)

    connection.commit()


def create_indexes(connection):
    cursor = connection.cursor()

    cursor.executescript("""
        CREATE INDEX idx_geo_feature_type
        ON geo_features(feature_type);

        CREATE INDEX idx_geo_coordinates
        ON geo_features(lat, lon);

        CREATE INDEX idx_poi_type
        ON pois(poi_type);

        CREATE INDEX idx_poi_coordinates
        ON pois(lat, lon);

        CREATE INDEX idx_settlement_coordinates
        ON settlements(lat, lon);

        CREATE INDEX idx_settlement_type
        ON settlements(place_type);

        CREATE INDEX idx_settlement_name
        ON settlements(name);
    """)

    connection.commit()


# ---------------------------------------------------------
# CSV HELPERS
# ---------------------------------------------------------

def valid_coordinate(value):
    try:
        number = float(value)
        return number
    except (TypeError, ValueError):
        return None


def import_geo_csv(connection, filename, database_category):
    csv_path = PROCESSED_DIR / filename

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV file: {csv_path}")

    inserted = 0
    batch = []

    print(f"\nImporting {filename} as {database_category}...")

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            lat = valid_coordinate(row.get("latitude"))
            lon = valid_coordinate(row.get("longitude"))

            if lat is None or lon is None:
                continue

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue

            batch.append((
                row.get("osm_id"),
                database_category,
                row.get("name") or None,
                lat,
                lon,
            ))

            if len(batch) >= BATCH_SIZE:
                connection.executemany("""
                    INSERT INTO geo_features
                    (osm_id, feature_type, name, lat, lon)
                    VALUES (?, ?, ?, ?, ?)
                """, batch)

                inserted += len(batch)
                batch.clear()

        if batch:
            connection.executemany("""
                INSERT INTO geo_features
                (osm_id, feature_type, name, lat, lon)
                VALUES (?, ?, ?, ?, ?)
            """, batch)

            inserted += len(batch)

    connection.commit()

    print(f"  Inserted {inserted:,} records.")
    return inserted


def import_poi_csv(connection, filename, category_mapping, source_type):
    csv_path = PROCESSED_DIR / filename

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV file: {csv_path}")

    inserted = 0
    skipped = 0
    batch = []

    print(f"\nImporting {filename} as points of interest...")

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            original_category = row.get("feature_value", "").strip()
            poi_type = category_mapping.get(original_category)

            if not poi_type:
                skipped += 1
                continue

            lat = valid_coordinate(row.get("latitude"))
            lon = valid_coordinate(row.get("longitude"))

            if lat is None or lon is None:
                skipped += 1
                continue

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                skipped += 1
                continue

            batch.append((
                row.get("osm_id"),
                poi_type,
                row.get("name") or None,
                lat,
                lon,
            ))

            if len(batch) >= BATCH_SIZE:
                connection.executemany("""
                    INSERT INTO pois
                    (osm_id, poi_type, name, lat, lon)
                    VALUES (?, ?, ?, ?, ?)
                """, batch)

                inserted += len(batch)
                batch.clear()

        if batch:
            connection.executemany("""
                INSERT INTO pois
                (osm_id, poi_type, name, lat, lon)
                VALUES (?, ?, ?, ?, ?)
            """, batch)

            inserted += len(batch)

    connection.commit()

    print(f"  Inserted {inserted:,} {source_type} records.")
    if skipped:
        print(f"  Skipped {skipped:,} unsupported or invalid records.")

    return inserted


# ---------------------------------------------------------
# SETTLEMENT EXTRACTION FROM EXISTING PBF
# ---------------------------------------------------------

def extract_settlements(connection):
    if not RAW_PBF.exists():
        raise FileNotFoundError(
            f"Existing OSM PBF file not found: {RAW_PBF}"
        )

    try:
        import osmium
    except ImportError as error:
        raise RuntimeError(
            "The osmium package is missing. "
            "Activate the backend virtual environment and install osmium."
        ) from error

    print("\nExtracting settlements from the existing Karnataka PBF...")
    print("This may take several minutes. Please let it finish.")

    class SettlementHandler(osmium.SimpleHandler):

        def __init__(self, db_connection):
            super().__init__()
            self.connection = db_connection
            self.batch = []
            self.inserted = 0

        def node(self, node):
            tags = node.tags

            place_type = tags.get("place")
            name = tags.get("name")

            if place_type not in SETTLEMENT_TYPES or not name:
                return

            if not node.location.valid():
                return

            lat = node.location.lat
            lon = node.location.lon

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return

            population_value = tags.get("population")
            population = None

            if population_value:
                try:
                    population = int(
                        population_value.replace(",", "").strip()
                    )
                except (ValueError, AttributeError):
                    population = None

            self.batch.append((
                str(node.id),
                name.strip(),
                place_type,
                lat,
                lon,
                population,
            ))

            if len(self.batch) >= BATCH_SIZE:
                self.flush()

        def flush(self):
            if not self.batch:
                return

            self.connection.executemany("""
                INSERT INTO settlements
                (osm_id, name, place_type, lat, lon, population)
                VALUES (?, ?, ?, ?, ?, ?)
            """, self.batch)

            self.inserted += len(self.batch)
            self.batch.clear()

        def finish(self):
            self.flush()

    handler = SettlementHandler(connection)

    handler.apply_file(str(RAW_PBF), locations=False)
    handler.finish()

    connection.commit()

    print(f"  Inserted {handler.inserted:,} settlements.")
    return handler.inserted


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

def validate_database(connection):
    cursor = connection.cursor()

    print("\nValidating the rebuilt database...")

    tables = [
        "geo_features",
        "pois",
        "settlements",
    ]

    counts = {}

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]

    for table, count in counts.items():
        print(f"  {table}: {count:,} records")

    if counts["geo_features"] == 0:
        raise RuntimeError(
            "Database validation failed: geo_features is empty.")

    if counts["pois"] == 0:
        raise RuntimeError("Database validation failed: pois is empty.")

    if counts["settlements"] == 0:
        raise RuntimeError("Database validation failed: settlements is empty.")

    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]

    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")

    print(f"  SQLite integrity: {integrity}")

    return counts


# ---------------------------------------------------------
# MAIN BUILD PROCESS
# ---------------------------------------------------------

def build_database():
    print("=" * 60)
    print("ROAM - KARNATAKA DATABASE BUILDER")
    print("=" * 60)

    required_files = [
        PROCESSED_DIR / "forests.csv",
        PROCESSED_DIR / "water_bodies.csv",
        PROCESSED_DIR / "tourist_places.csv",
        PROCESSED_DIR / "amenities.csv",
        RAW_PBF,
    ]

    for path in required_files:
        if not path.exists():
            raise FileNotFoundError(f"Required source file missing: {path}")

    if TEMP_DATABASE_PATH.exists():
        TEMP_DATABASE_PATH.unlink()

    connection = None

    try:
        connection = sqlite3.connect(TEMP_DATABASE_PATH)

        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=NORMAL")

        create_tables(connection)

        # Geographic features
        import_geo_csv(connection, "forests.csv", "forest")
        import_geo_csv(connection, "water_bodies.csv", "water")

        # Tourist locations
        import_poi_csv(
            connection,
            "tourist_places.csv",
            TOURISM_MAPPING,
            "tourist"
        )

        # Food, fuel and other amenities
        import_poi_csv(
            connection,
            "amenities.csv",
            AMENITY_MAPPING,
            "amenity"
        )

        # Real named settlements from OSM
        extract_settlements(connection)

        create_indexes(connection)

        counts = validate_database(connection)

        connection.close()
        connection = None

        # Preserve an existing non-empty database before replacing it.
        if DATABASE_PATH.exists() and DATABASE_PATH.stat().st_size > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = DATA_DIR / f"karnataka_backup_{timestamp}.db"
            shutil.copy2(DATABASE_PATH, backup_path)
            print(f"\nPrevious database backed up to: {backup_path}")

        # Replace the target only after the new database passes validation.
        os.replace(TEMP_DATABASE_PATH, DATABASE_PATH)

        print("\n" + "=" * 60)
        print("DATABASE BUILD COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Database: {DATABASE_PATH}")
        print(f"File size: {DATABASE_PATH.stat().st_size:,} bytes")
        print(f"Total geographic features: {counts['geo_features']:,}")
        print(f"Total points of interest: {counts['pois']:,}")
        print(f"Total settlements: {counts['settlements']:,}")

    except Exception:
        if connection is not None:
            connection.close()

        if TEMP_DATABASE_PATH.exists():
            TEMP_DATABASE_PATH.unlink()

        print("\nDatabase build failed.")
        print("The existing karnataka.db has not been replaced.")
        raise


if __name__ == "__main__":
    build_database()
