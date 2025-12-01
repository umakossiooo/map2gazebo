import json
import sys
from shapely.geometry import Polygon
from shapely.ops import unary_union

def merge_polygons(input_path, output_path):
    print("[INFO] Loading polygons:", input_path)

    with open(input_path, "r") as f:
        data = json.load(f)

    merged = {}

    print("[INFO] Merging polygons by road ID...")

    for way_id, entry in data.items():
        polys = []

        # Each entry["polygon"] is a list of [x,y]
        poly_coords = entry["polygon"]

        try:
            p = Polygon(poly_coords)
            if p.is_valid and not p.is_empty:
                polys.append(p)
        except Exception as e:
            print(f"  [WARN] Invalid polygon for road {way_id}: {e}")
            continue

        # Unary union merges all segments for this road
        if len(polys) > 0:
            merged_poly = unary_union(polys)

            # Handle MultiPolygon (unlikely but possible)
            if hasattr(merged_poly, "geoms"):
                merged_coords = [list(poly.exterior.coords) for poly in merged_poly.geoms]
            else:
                merged_coords = [list(merged_poly.exterior.coords)]

            merged[way_id] = {
                "merged_polygons": merged_coords,
                "tags": entry.get("tags", {}),
                "width": entry.get("width", None)
            }

    print("[INFO] Saving merged polygons:", output_path)

    with open(output_path, "w") as f:
        json.dump(merged, f, indent=4)

    print("[DONE] Polygon merging finished successfully.")


def main():
    if len(sys.argv) != 3:
        print("Usage: python merge_polygons.py <input_road_polygons.json> <output_merged.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    merge_polygons(input_path, output_path)


if __name__ == "__main__":
    main()
