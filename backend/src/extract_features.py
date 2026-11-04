
import csv
import osmium
from pathlib import Path

# --------------------------------------------------
# ROAM - Karnataka Geographic Feature Extraction v2
# --------------------------------------------------

DATA_FILE = Path("data/raw/karnataka-latest.osm.pbf")
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ROAD_TYPES = {
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "unclassified", "residential",
    "living_street", "service",
    "road", "track"
}

FOREST_TYPES = {
    "wood", "scrub", "grassland",
    "wetland", "tree_row", "forest",
    "orchard", "grass", "meadow"
}

WATER_TYPES = {
    "water", "river", "stream",
    "canal", "waterfall", "riverbank",
    "reservoir", "basin"
}

TOURISM_TYPES = {
    "viewpoint", "attraction",
    "museum", "picnic_site",
    "zoo", "theme_park",
    "camp_site", "information"
}

AMENITY_TYPES = {
    "restaurant", "cafe", "fast_food",
    "fuel", "toilets", "drinking_water",
    "parking"
}

FIELDS = [
    "osm_type",
    "osm_id",
    "feature_type",
    "feature_value",
    "name",
    "latitude",
    "longitude",
    "geometry_wkt"
]


class ROAMExtractor(osmium.SimpleHandler):

    def __init__(self):
        super().__init__()

        self.files = {}
        self.writers = {}

        self.counts = {
            "roads": 0,
            "forests": 0,
            "water_bodies": 0,
            "tourist_places": 0,
            "amenities": 0
        }

        self.geometry_counts = {
            "POINT": 0,
            "LINESTRING": 0,
            "POLYGON": 0
        }

        self.open_output_files()

    def open_output_files(self):

        for category in self.counts:

            path = OUTPUT_DIR / f"{category}.csv"

            file = open(
                path,
                "w",
                newline="",
                encoding="utf-8"
            )

            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS
            )

            writer.writeheader()

            self.files[category] = file
            self.writers[category] = writer

    def close_output_files(self):

        for file in self.files.values():
            file.close()

    def get_name(self, tags):
        return tags.get("name", "")

    def create_geometry(self, coordinates, allow_polygon=False):

        if not coordinates:
            return None

        points = [
            f"{lon} {lat}"
            for lon, lat in coordinates
        ]

        # Closed ways representing areas become polygons.
        is_closed = (
            len(coordinates) >= 4
            and coordinates[0] == coordinates[-1]
        )

        if allow_polygon and is_closed:

            ring = ", ".join(points)

            geometry = f"POLYGON(({ring}))"
            geometry_type = "POLYGON"

        else:

            if len(coordinates) < 2:
                return None

            geometry = (
                f"LINESTRING({', '.join(points)})"
            )

            geometry_type = "LINESTRING"

        return geometry, geometry_type

    def write_feature(
        self,
        category,
        osm_type,
        osm_id,
        feature_type,
        feature_value,
        name,
        latitude,
        longitude,
        geometry_wkt,
        geometry_type
    ):

        self.writers[category].writerow({
            "osm_type": osm_type,
            "osm_id": osm_id,
            "feature_type": feature_type,
            "feature_value": feature_value,
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "geometry_wkt": geometry_wkt
        })

        self.counts[category] += 1
        self.geometry_counts[geometry_type] += 1

    def node(self, node):

        if not node.location.valid():
            return

        latitude = node.location.lat
        longitude = node.location.lon
        tags = node.tags
        name = self.get_name(tags)

        point_wkt = f"POINT({longitude} {latitude})"

        natural = tags.get("natural", "")

        if natural in {"tree", "scrub", "water"}:

            category = (
                "water_bodies"
                if natural == "water"
                else "forests"
            )

            self.write_feature(
                category, "node", node.id,
                "natural", natural, name,
                latitude, longitude,
                point_wkt, "POINT"
            )

        tourism = tags.get("tourism", "")

        if tourism in TOURISM_TYPES:

            self.write_feature(
                "tourist_places", "node", node.id,
                "tourism", tourism, name,
                latitude, longitude,
                point_wkt, "POINT"
            )

        amenity = tags.get("amenity", "")

        if amenity in AMENITY_TYPES:

            self.write_feature(
                "amenities", "node", node.id,
                "amenity", amenity, name,
                latitude, longitude,
                point_wkt, "POINT"
            )

    def way(self, way):

        tags = way.tags
        coordinates = []

        for node in way.nodes:

            if node.location.valid():

                coordinates.append((
                    node.location.lon,
                    node.location.lat
                ))

        if len(coordinates) < 2:
            return

        longitude = sum(
            point[0] for point in coordinates
        ) / len(coordinates)

        latitude = sum(
            point[1] for point in coordinates
        ) / len(coordinates)

        name = self.get_name(tags)

        # Roads are always represented as lines.
        highway = tags.get("highway", "")

        if highway in ROAD_TYPES:

            result = self.create_geometry(
                coordinates,
                allow_polygon=False
            )

            if result:

                geometry, geometry_type = result

                self.write_feature(
                    "roads", "way", way.id,
                    "highway", highway, name,
                    latitude, longitude,
                    geometry, geometry_type
                )

        # Forest and green areas.
        natural = tags.get("natural", "")
        landuse = tags.get("landuse", "")

        forest_value = None
        forest_tag = None

        if natural in FOREST_TYPES:
            forest_value = natural
            forest_tag = "natural"

        elif landuse in FOREST_TYPES:
            forest_value = landuse
            forest_tag = "landuse"

        if forest_value:

            result = self.create_geometry(
                coordinates,
                allow_polygon=True
            )

            if result:

                geometry, geometry_type = result

                self.write_feature(
                    "forests", "way", way.id,
                    forest_tag, forest_value, name,
                    latitude, longitude,
                    geometry, geometry_type
                )

        # Water features.
        waterway = tags.get("waterway", "")
        natural_water = tags.get("natural", "")
        water_landuse = tags.get("landuse", "")

        water_value = None
        water_tag = None
        allow_polygon = False

        if waterway in WATER_TYPES:
            water_value = waterway
            water_tag = "waterway"

        elif natural_water == "water":
            water_value = natural_water
            water_tag = "natural"
            allow_polygon = True

        elif water_landuse in {"basin", "reservoir"}:
            water_value = water_landuse
            water_tag = "landuse"
            allow_polygon = True

        if water_value:

            result = self.create_geometry(
                coordinates,
                allow_polygon=allow_polygon
            )

            if result:

                geometry, geometry_type = result

                self.write_feature(
                    "water_bodies", "way", way.id,
                    water_tag, water_value, name,
                    latitude, longitude,
                    geometry, geometry_type
                )

        # Tourist places.
        tourism = tags.get("tourism", "")

        if tourism in TOURISM_TYPES:

            result = self.create_geometry(
                coordinates,
                allow_polygon=True
            )

            if result:

                geometry, geometry_type = result

                self.write_feature(
                    "tourist_places", "way", way.id,
                    "tourism", tourism, name,
                    latitude, longitude,
                    geometry, geometry_type
                )

        # Amenities.
        amenity = tags.get("amenity", "")

        if amenity in AMENITY_TYPES:

            result = self.create_geometry(
                coordinates,
                allow_polygon=True
            )

            if result:

                geometry, geometry_type = result

                self.write_feature(
                    "amenities", "way", way.id,
                    "amenity", amenity, name,
                    latitude, longitude,
                    geometry, geometry_type
                )

    def relation(self, relation):
        # Multipolygon relations are reserved for a later stage.
        pass


def main():

    if not DATA_FILE.exists():
        print("ERROR: Karnataka PBF file not found.")
        print(DATA_FILE.resolve())
        return

    print("ROAM extraction v2 started.")
    print("Reading:", DATA_FILE.resolve())
    print("Output:", OUTPUT_DIR.resolve())
    print("\nProcessing geographic data...\n")

    extractor = ROAMExtractor()

    try:
        extractor.apply_file(
            str(DATA_FILE),
            locations=True
        )

    finally:
        extractor.close_output_files()

    print("\n========== EXTRACTION REPORT ==========")

    for category, count in extractor.counts.items():
        print(f"{category}: {count:,}")

    print("\nGeometry distribution:")

    for geometry, count in extractor.geometry_counts.items():
        print(f"{geometry}: {count:,}")

    print("\nGenerated files:")

    for category in extractor.counts:

        path = OUTPUT_DIR / f"{category}.csv"

        print(
            f"{path.name}: {path.stat().st_size:,} bytes"
        )

    print("\nROAM extraction v2 completed!")


if __name__ == "__main__":
    main()
