
"""
ROAM - Karnataka OSM Data Pipeline

Downloads and processes the Karnataka OpenStreetMap dataset into a local SQLite
database for fast, offline scenic scoring and POI queries.

Usage (run once from the backend directory):
    python -m src.data_pipeline

Data source: Geofabrik OpenStreetMap extracts
  https://download.geofabrik.de/asia/india/karnataka-latest.osm.bz2

Processing approach:
  - Parse OSM XML (bz2 compressed) using Python's standard xml + bz2 modules
  - No external C libraries required (no pyosmium dependency)
  - Extracts: geo features, POIs, settlements into SQLite
  - Estimated download size: ~80–120 MB compressed
  - Estimated DB size after processing: ~40–80 MB
  - One-time setup; subsequent ROAM calls query the local DB (no internet needed)
"""

import bz2
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

# --------------------------------------------------
# PATHS
# --------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "karnataka.db"
OSM_BZ2_PATH = DATA_DIR / "karnataka-latest.osm.bz2"

OSM_URL = (
    "https://download.geofabrik.de/asia/india/"
    "karnataka-latest.osm.bz2"
)

HEADERS = {"User-Agent": "ROAM-Scenic-Road-Trip-Planner/1.0"}


# --------------------------------------------------
# OSM TAG MAPPING
# --------------------------------------------------

# Maps OSM tag combinations to ROAM feature types
GEO_FEATURE_RULES = [
    # (tag_key, tag_value_or_None_for_any, roam_feature_type)
    ("natural",  "wood",      "forest"),
    ("landuse",  "forest",    "forest"),
    ("natural",  "scrub",     "forest"),
    ("natural",  "water",     "water"),
    ("natural",  "wetland",   "water"),
    ("waterway", "river",     "water"),
    ("waterway", "stream",    "water"),
    ("natural",  "peak",      "mountain"),
    ("natural",  "cliff",     "mountain"),
    ("natural",  "ridge",     "mountain"),
    ("natural",  "valley",    "mountain"),
    ("landuse",  "farmland",  "farmland"),
    ("natural",  "grassland", "farmland"),
    ("natural",  "heath",     "farmland"),
    ("landuse",  "residential","urban"),
    ("landuse",  "commercial", "urban"),
    ("landuse",  "industrial", "urban"),
    ("natural",  "beach",     "coastal"),
    ("natural",  "coastline", "coastal"),
]

POI_RULES = [
    ("amenity", "fuel",        "fuel"),
    ("amenity", "restaurant",  "food"),
    ("amenity", "cafe",        "food"),
    ("amenity", "fast_food",   "food"),
    ("amenity", "hotel",       "hotel"),
    ("tourism", "hotel",       "hotel"),
    ("tourism", "guest_house", "hotel"),
    ("tourism", "viewpoint",   "viewpoint"),
    ("tourism", "attraction",  "viewpoint"),
    ("natural", "peak",        "viewpoint"),
    ("amenity", "hospital",    "medical"),
    ("amenity", "pharmacy",    "medical"),
]

SETTLEMENT_PLACE_TYPES = {"city", "town", "village", "hamlet"}


# --------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS geo_features (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    osm_id       INTEGER,
    feature_type TEXT    NOT NULL,
    name         TEXT,
    lat          REAL    NOT NULL,
    lon          REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS pois (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    osm_id       INTEGER,
    poi_type     TEXT    NOT NULL,
    name         TEXT,
    lat          REAL    NOT NULL,
    lon          REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS settlements (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    osm_id       INTEGER,
    name         TEXT    NOT NULL,
    place_type   TEXT,
    lat          REAL    NOT NULL,
    lon          REAL    NOT NULL,
    population   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_geo_lat_lon   ON geo_features (lat, lon);
CREATE INDEX IF NOT EXISTS idx_geo_type      ON geo_features (feature_type);
CREATE INDEX IF NOT EXISTS idx_poi_lat_lon   ON pois (lat, lon);
CREATE INDEX IF NOT EXISTS idx_poi_type      ON pois (poi_type);
CREATE INDEX IF NOT EXISTS idx_settle_lat_lon ON settlements (lat, lon);
"""


def init_database() -> sqlite3.Connection:
    """Create database and tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    print(f"[DB] Database ready at {DB_PATH}")
    return conn


# --------------------------------------------------
# DOWNLOAD
# --------------------------------------------------

def download_osm_data():
    """Download Karnataka OSM bz2 file from Geofabrik."""

    if OSM_BZ2_PATH.exists():
        size_mb = OSM_BZ2_PATH.stat().st_size / 1_048_576
        print(f"[DOWNLOAD] Found existing file ({size_mb:.1f} MB). Skipping download.")
        return

    print(f"[DOWNLOAD] Downloading Karnataka OSM data from Geofabrik...")
    print(f"[DOWNLOAD] URL: {OSM_URL}")
    print("[DOWNLOAD] This may take several minutes depending on your connection.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(OSM_URL, headers=HEADERS, stream=True, timeout=300)
        response.raise_for_status()

        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        start = time.monotonic()

        with open(OSM_BZ2_PATH, "wb") as file:
            for chunk in response.iter_content(chunk_size=1_048_576):  # 1 MB chunks
                file.write(chunk)
                downloaded += len(chunk)

                if total:
                    pct = downloaded / total * 100
                    elapsed = time.monotonic() - start
                    speed = downloaded / elapsed / 1_048_576
                    print(f"\r[DOWNLOAD] {pct:.1f}% — {downloaded / 1_048_576:.1f} MB"
                          f" / {total / 1_048_576:.1f} MB — {speed:.1f} MB/s", end="")

        print(f"\n[DOWNLOAD] Download complete: {downloaded / 1_048_576:.1f} MB")

    except requests.RequestException as error:
        print(f"\n[DOWNLOAD] ERROR: {error}")
        if OSM_BZ2_PATH.exists():
            OSM_BZ2_PATH.unlink()
        raise


# --------------------------------------------------
# TAG MATCHING HELPERS
# --------------------------------------------------

def match_geo_feature(tags: dict) -> str | None:
    """Return the ROAM feature type for a node/way's tags, or None."""
    for key, value, feature_type in GEO_FEATURE_RULES:
        if key in tags:
            if value is None or tags[key] == value:
                return feature_type
    return None


def match_poi(tags: dict) -> str | None:
    """Return the ROAM POI type, or None."""
    for key, value, poi_type in POI_RULES:
        if key in tags and tags[key] == value:
            return poi_type
    return None


def match_settlement(tags: dict) -> str | None:
    """Return the place type if this is a settlement node, or None."""
    place = tags.get("place")
    return place if place in SETTLEMENT_PLACE_TYPES else None


# --------------------------------------------------
# OSM XML PARSER
# --------------------------------------------------

def parse_and_load(conn: sqlite3.Connection):
    """
    Parse Karnataka OSM bz2 XML and load into SQLite.

    Processes nodes only (ways/relations need centroid calculation which
    requires a second pass — nodes are sufficient for point-based features).
    For polygon features (forests, lakes), we use their member nodes.
    """

    geo_batch = []
    poi_batch = []
    settle_batch = []

    BATCH_SIZE = 10_000
    total_nodes = 0
    total_ways = 0
    inserted_geo = 0
    inserted_poi = 0
    inserted_settle = 0

    print("[PARSE] Parsing OSM XML (this may take 10–30 minutes)...")
    start = time.monotonic()

    # Node coordinates cache for way centroid calculation
    node_coords: dict[int, tuple[float, float]] = {}

    def flush_batches():
        nonlocal inserted_geo, inserted_poi, inserted_settle
        if geo_batch:
            conn.executemany(
                "INSERT INTO geo_features (osm_id, feature_type, name, lat, lon) "
                "VALUES (?, ?, ?, ?, ?)", geo_batch
            )
            inserted_geo += len(geo_batch)
            geo_batch.clear()
        if poi_batch:
            conn.executemany(
                "INSERT INTO pois (osm_id, poi_type, name, lat, lon) "
                "VALUES (?, ?, ?, ?, ?)", poi_batch
            )
            inserted_poi += len(poi_batch)
            poi_batch.clear()
        if settle_batch:
            conn.executemany(
                "INSERT INTO settlements (osm_id, name, place_type, lat, lon, population) "
                "VALUES (?, ?, ?, ?, ?, ?)", settle_batch
            )
            inserted_settle += len(settle_batch)
            settle_batch.clear()
        conn.commit()

    print("[PARSE] Reading compressed file...")

    with bz2.open(OSM_BZ2_PATH, "rb") as raw:

        context = ET.iterparse(raw, events=("start", "end"))
        current_element = None
        current_tags = {}

        for event, elem in context:

            if event == "start":
                if elem.tag == "node":
                    current_element = elem
                    current_tags = {}

                elif elem.tag == "way":
                    current_element = elem
                    current_tags = {}

            elif event == "end":

                if elem.tag == "tag" and current_element is not None:
                    current_tags[elem.get("k", "")] = elem.get("v", "")

                elif elem.tag == "node":
                    total_nodes += 1

                    try:
                        lat = float(elem.get("lat", 0))
                        lon = float(elem.get("lon", 0))
                        osm_id = int(elem.get("id", 0))
                    except (ValueError, TypeError):
                        elem.clear()
                        current_element = None
                        continue

                    # Cache coordinates for way processing
                    node_coords[osm_id] = (lat, lon)

                    # Keep cache bounded
                    if len(node_coords) > 2_000_000:
                        # Remove oldest half (simple approximation)
                        keys = list(node_coords.keys())
                        for k in keys[:1_000_000]:
                            del node_coords[k]

                    name = current_tags.get("name", "")

                    # Check for geo feature
                    feature_type = match_geo_feature(current_tags)
                    if feature_type:
                        geo_batch.append((osm_id, feature_type, name, lat, lon))

                    # Check for POI
                    poi_type = match_poi(current_tags)
                    if poi_type:
                        poi_batch.append((osm_id, poi_type, name, lat, lon))

                    # Check for settlement
                    place_type = match_settlement(current_tags)
                    if place_type and name:
                        try:
                            pop = int(current_tags.get("population", 0))
                        except ValueError:
                            pop = 0
                        settle_batch.append((osm_id, name, place_type, lat, lon, pop))

                    current_element = None
                    current_tags = {}

                    if total_nodes % 500_000 == 0:
                        flush_batches()
                        elapsed = time.monotonic() - start
                        print(f"\r[PARSE] Nodes: {total_nodes:,} | "
                              f"Geo: {inserted_geo + len(geo_batch):,} | "
                              f"POI: {inserted_poi + len(poi_batch):,} | "
                              f"Settle: {inserted_settle + len(settle_batch):,} | "
                              f"{elapsed:.0f}s", end="")

                    elem.clear()

                elif elem.tag == "way":
                    total_ways += 1
                    name = current_tags.get("name", "")
                    osm_id = int(elem.get("id", 0) or 0)

                    feature_type = match_geo_feature(current_tags)
                    poi_type = match_poi(current_tags)

                    if feature_type or poi_type:
                        # Compute centroid from member node refs
                        nd_refs = [
                            int(child.get("ref", 0))
                            for child in elem
                            if child.tag == "nd"
                        ]
                        coords = [node_coords[ref] for ref in nd_refs if ref in node_coords]

                        if coords:
                            lat = sum(c[0] for c in coords) / len(coords)
                            lon = sum(c[1] for c in coords) / len(coords)

                            if feature_type:
                                geo_batch.append((osm_id, feature_type, name, lat, lon))
                            if poi_type:
                                poi_batch.append((osm_id, poi_type, name, lat, lon))

                    current_element = None
                    current_tags = {}
                    elem.clear()

        flush_batches()

    elapsed = time.monotonic() - start
    print(f"\n[PARSE] Complete in {elapsed:.0f}s")
    print(f"[PARSE] Nodes processed: {total_nodes:,}")
    print(f"[PARSE] Ways processed:  {total_ways:,}")
    print(f"[PARSE] Geo features:    {inserted_geo:,}")
    print(f"[PARSE] POIs:            {inserted_poi:,}")
    print(f"[PARSE] Settlements:     {inserted_settle:,}")


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

def run_pipeline():
    """Full pipeline: download → parse → index → done."""

    print("=" * 60)
    print("  ROAM — Karnataka OSM Data Pipeline")
    print("=" * 60)

    if DB_PATH.exists() and DB_PATH.stat().st_size > 10_000_000:
        size_mb = DB_PATH.stat().st_size / 1_048_576
        print(f"\n[INFO] Database already exists ({size_mb:.1f} MB).")
        answer = input("[INFO] Re-build from scratch? [y/N]: ").strip().lower()
        if answer != "y":
            print("[INFO] Skipping. Existing database will be used.")
            return

        DB_PATH.unlink()
        print("[INFO] Existing database removed.")

    download_osm_data()

    conn = init_database()

    try:
        parse_and_load(conn)
    finally:
        conn.close()

    size_mb = DB_PATH.stat().st_size / 1_048_576
    print(f"\n[DONE] Database built: {DB_PATH} ({size_mb:.1f} MB)")
    print("[DONE] ROAM scenic intelligence is now enabled.")


if __name__ == "__main__":
    run_pipeline()
