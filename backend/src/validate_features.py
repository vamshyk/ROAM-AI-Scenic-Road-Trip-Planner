
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/processed")

files = [
    "roads.csv",
    "forests.csv",
    "water_bodies.csv",
    "tourist_places.csv",
    "amenities.csv"
]

print("\n========== ROAM GEOMETRY VALIDATION ==========\n")

for filename in files:

    path = DATA_DIR / filename

    print(f"\n--- {filename} ---")

    if not path.exists():
        print("ERROR: File not found")
        continue

    df = pd.read_csv(path)

    print(f"Total records: {len(df):,}")

    print("\nGeometry distribution:")

    geometry_types = (
        df["geometry_wkt"]
        .str.extract(r"^([A-Z]+)")
        [0]
        .value_counts()
    )

    print(geometry_types.to_string())

    print("\nMissing coordinates:",
          df[["latitude", "longitude"]].isna().any(axis=1).sum())

    print("Missing geometries:",
          df["geometry_wkt"].isna().sum())

print("\n========== VALIDATION COMPLETE ==========")
