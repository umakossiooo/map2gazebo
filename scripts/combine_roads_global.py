#!/usr/bin/env python3
"""
combine_roads_global.py

Toma todos los polígonos de calles de road_polygons_merged.json,
los fusiona con shapely (unary_union) y genera un archivo
roads_global.json con una lista de polígonos finales (sin solapes).

Uso:
  python scripts/combine_roads_global.py maps/road_polygons_merged.json maps/roads_global.json
"""

import sys
import json
from pathlib import Path

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union


def load_polygons(merged_path: Path):
    with merged_path.open("r") as f:
        data = json.load(f)

    polys = []
    for wid, entry in data.items():
        merged_polys = entry.get("merged_polygons", [])
        for coords in merged_polys:
            if len(coords) < 3:
                continue
            try:
                poly = Polygon(coords)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_empty:
                    continue
                polys.append(poly)
            except Exception:
                continue
    return polys


def polygons_to_coords(poly_obj):
    """Convierte Polygon o MultiPolygon a lista de listas de [x,y]."""
    result = []

    if isinstance(poly_obj, Polygon):
        coords = list(poly_obj.exterior.coords)
        result.append([[float(x), float(y)] for x, y in coords])

    elif isinstance(poly_obj, MultiPolygon):
        for p in poly_obj.geoms:
            coords = list(p.exterior.coords)
            result.append([[float(x), float(y)] for x, y in coords])

    else:
        raise TypeError(f"Unexpected geometry type: {type(poly_obj)}")

    return result


def main():
    if len(sys.argv) != 3:
        print("Usage: python combine_roads_global.py <road_polygons_merged.json> <roads_global.json>")
        sys.exit(1)

    merged_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    print(f"[INFO] Loading merged road polygons from: {merged_path}")
    polys = load_polygons(merged_path)
    print(f"[INFO] Loaded {len(polys)} polygons")

    if not polys:
        print("[ERROR] No polygons found, aborting.")
        sys.exit(1)

    print("[INFO] Computing unary_union (global fusion)...")
    unioned = unary_union(polys)

    print("[INFO] Converting union geometry back to coordinate lists...")
    all_coords = polygons_to_coords(unioned)

    out_data = {
        "polygons": all_coords,
        "source": str(merged_path)
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(out_data, f)

    print(f"[OK] Global roads polygon saved to: {out_path}")
    print(f"     Total polygons after union: {len(all_coords)}")


if __name__ == "__main__":
    main()
