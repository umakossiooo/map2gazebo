#!/usr/bin/env python3
"""
generate_clean_sidewalks.py

Generates a clean sidewalk layer by:
1. Taking the raw sidewalk polygons (strips along roads).
2. Subtracting the ENTIRE road network footprint.
3. This ensures sidewalks never overlap ANY road (even at intersections).

Usage:
  python scripts/generate_clean_sidewalks.py maps/road_polygons.json maps/sidewalk_polygons.json maps/sidewalk_polygons_clean.json
"""

import argparse
import json
import sys
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

def load_polygons(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    
    polys = []
    for entry in data.values():
        # Handle new format "polygons" (list of lists) OR old format "polygon" (list)
        coords_list = []
        if "polygons" in entry:
            coords_list = entry["polygons"]
        elif "polygon" in entry:
            coords_list = [entry["polygon"]]
            
        for coords in coords_list:
            if not coords or len(coords) < 3:
                continue
            try:
                p = Polygon(coords)
                if p.is_valid and not p.is_empty:
                    polys.append(p)
                else:
                    # Try buffer(0) to fix invalid
                    p = p.buffer(0)
                    if p.is_valid and not p.is_empty:
                        polys.append(p)
            except:
                pass
    return polys

def main():
    if len(sys.argv) != 4:
        print("Usage: python generate_clean_sidewalks.py <roads.json> <sidewalks.json> <output.json>")
        sys.exit(1)

    roads_file = sys.argv[1]
    sidewalks_file = sys.argv[2]
    output_file = sys.argv[3]

    print(f"[INFO] Loading roads from {roads_file}...")
    road_polys = load_polygons(roads_file)
    print(f"       Found {len(road_polys)} road segments.")

    print(f"[INFO] Loading sidewalks from {sidewalks_file}...")
    sidewalk_polys = load_polygons(sidewalks_file)
    print(f"       Found {len(sidewalk_polys)} sidewalk segments.")

    print("[INFO] Merging all roads into a single footprint...")
    all_roads = unary_union(road_polys)

    print("[INFO] Merging all sidewalks...")
    all_sidewalks = unary_union(sidewalk_polys)

    print("[INFO] Subtracting Roads from Sidewalks (Cleaning)...")
    clean_sidewalks = all_sidewalks.difference(all_roads)

    # Convert back to JSON structure (Compatible with build_sdf expectations)
    # We group everything into one "sidewalks" entry with multiple polygons
    output_data = {
        "sidewalks_clean": {
            "merged_polygons": [],
            "tags": {"type": "sidewalk_clean"}
        }
    }
    
    # difference() might return Polygon or MultiPolygon
    final_polys = []
    if isinstance(clean_sidewalks, Polygon):
        final_polys = [clean_sidewalks]
    elif isinstance(clean_sidewalks, MultiPolygon):
        final_polys = list(clean_sidewalks.geoms)
    
    print(f"[INFO] Result: {len(final_polys)} clean sidewalk chunks.")

    for poly in final_polys:
        if poly.is_empty: 
            continue
        coords = list(poly.exterior.coords)
        output_data["sidewalks_clean"]["merged_polygons"].append(coords)

    print(f"[INFO] Saving to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=4)

    print("[DONE]")

if __name__ == "__main__":
    main()

