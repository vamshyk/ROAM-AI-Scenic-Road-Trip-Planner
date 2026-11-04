
import osmium
from pathlib import Path
from collections import Counter

# Path to the Karnataka OpenStreetMap dataset
DATA_FILE = Path("data/raw/karnataka-latest.osm.pbf")


class OSMInspector(osmium.SimpleHandler):

    def __init__(self):
        super().__init__()

        self.counts = Counter()
        self.features = Counter()

    def inspect_tags(self, tags):
        for key in [
            "highway",
            "landuse",
            "natural",
            "waterway",
            "tourism",
            "amenity"
        ]:
            if key in tags:
                self.features[key] += 1

    def node(self, node):
        self.counts["Nodes"] += 1
        self.inspect_tags(node.tags)

    def way(self, way):
        self.counts["Ways"] += 1
        self.inspect_tags(way.tags)

    def relation(self, relation):
        self.counts["Relations"] += 1
        self.inspect_tags(relation.tags)


def main():

    if not DATA_FILE.exists():
        print("ERROR: Dataset file not found!")
        print("Expected location:", DATA_FILE.resolve())
        return

    print("Starting Karnataka OSM inspection...")
    print("Dataset:", DATA_FILE.resolve())
    print("Please wait. Reading the PBF file...\n")

    inspector = OSMInspector()

    inspector.apply_file(str(DATA_FILE))

    print("\n========== OSM INSPECTION REPORT ==========")

    print("\nMap elements:")

    for name, count in inspector.counts.items():
        print(f"{name}: {count:,}")

    print("\nGeographic feature categories:")

    for name, count in inspector.features.most_common():
        print(f"{name}: {count:,}")

    print("\n===========================================")
    print("Dataset inspection completed successfully!")


if __name__ == "__main__":
    main()
