import json
import sys
from shapely.geometry import Polygon
from shapely.ops import unary_union


def merge_polygons(input_path, output_path, merge_by_name=True):
    print("[INFO] Loading polygons:", input_path)

    with open(input_path, "r") as f:
        data = json.load(f)

    groups = {}
    strategy = "street name" if merge_by_name else "road ID"
    print(f"[INFO] Merging polygons by {strategy}...")

    for way_id, entry in data.items():
        poly_coords = entry["polygon"]
        tags = entry.get("tags", {})

        try:
            poly = Polygon(poly_coords)
        except Exception as exc:
            print(f"  [WARN] Invalid polygon for road {way_id}: {exc}")
            continue

        if poly.is_empty or not poly.is_valid:
            continue

        name = tags.get("name") if merge_by_name else None
        key = name if name else way_id

        if key not in groups:
            groups[key] = {
                "polygons": [],
                "tags": tags,
                "widths": [],
                "source_way_ids": []
            }

        groups[key]["polygons"].append(poly)
        groups[key]["source_way_ids"].append(way_id)
        if entry.get("width") is not None:
            groups[key]["widths"].append(entry["width"])

    merged = {}

    for key, info in groups.items():
        merged_poly = unary_union(info["polygons"])

        if merged_poly.is_empty:
            continue

        if hasattr(merged_poly, "geoms"):
            merged_coords = [list(poly.exterior.coords) for poly in merged_poly.geoms]
        else:
            merged_coords = [list(merged_poly.exterior.coords)]

        width_value = info["widths"][0] if info["widths"] else None

        merged[key] = {
            "merged_polygons": merged_coords,
            "tags": info.get("tags", {}),
            "width": width_value,
            "source_way_ids": info.get("source_way_ids", [])
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

    merge_polygons(input_path, output_path, merge_by_name=True)


if __name__ == "__main__":
    main()
