
import osmium
from pathlib import Path
from collections import Counter

DATA_FILE = Path("data/raw/karnataka-latest.osm.pbf")

TAG_KEYS = [
    "highway",
    "landuse",
    "natural",
    "waterway",
    "tourism",
    "amenity"
]


class TagInspector(osmium.SimpleHandler):

    def __init__(self):
        super().__init__()
        self.tag_values = {
            key: Counter() for key in TAG_KEYS
        }

    def inspect(self, tags):
        for key in TAG_KEYS:
            value = tags.get(key)

            if value:
                self.tag_values[key][value] += 1

    def node(self, node):
        self.inspect(node.tags)

    def way(self, way):
        self.inspect(way.tags)

    def relation(self, relation):
        self.inspect(relation.tags)


def main():

    if not DATA_FILE.exists():
        print("ERROR: Dataset not found:", DATA_FILE.resolve())
        return

    inspector = TagInspector()

    print("Inspecting OSM tag values...")
    print("This may take a few minutes.\n")

    inspector.apply_file(str(DATA_FILE))

    for key, values in inspector.tag_values.items():

        print(f"\n========== {key.upper()} ==========")

        for value, count in values.most_common(25):
            print(f"{value}: {count:,}")

    print("\nTag inspection completed!")


if __name__ == "__main__":
    main()
