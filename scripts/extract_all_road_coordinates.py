#!/usr/bin/env python3
"""Extract ALL coordinates within the road mesh/road area.
Samples points inside road polygons to get complete coverage of the road area."""

import json
import sys
from pathlib import Path
from typing import List, Tuple, Set
from shapely.geometry import Polygon, Point
from polygon_utils import load_polygons

# Constants
COORDINATE_PRECISION = 10
GRID_RESOLUTION = 0.5  # Sample points every N meters (grid spacing)


def sample_points_inside_polygon(polygon: Polygon, resolution: float) -> List[Tuple[float, float]]:
    """Sample points inside a polygon using a grid.
    
    Creates a grid of points within the polygon bounds and filters to only
    include points that are inside the polygon (within the edges).
    
    Args:
        polygon: Shapely Polygon to sample
        resolution: Grid spacing in meters
        
    Returns:
        List of coordinate tuples inside the polygon
    """
    points = []
    minx, miny, maxx, maxy = polygon.bounds
    
    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            point = Point(x, y)
            if polygon.contains(point) or polygon.touches(point):
                points.append((round(x, COORDINATE_PRECISION), 
                              round(y, COORDINATE_PRECISION)))
            y += resolution
        x += resolution
    
    return points


def extract_all_road_coordinates(polygons_file: Path) -> List[Tuple[float, float]]:
    """Extract ALL coordinates within the road mesh/road area.
    
    Samples points inside all road polygons using a grid to get complete
    coverage of the road area. All coordinates are unique (no duplicates).
    This extracts all coordinates that cover the road mesh area (within the edges).
    
    Args:
        polygons_file: Path to road_polygons_merged.json file
        
    Returns:
        List of unique coordinate tuples sorted by (x, y)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is invalid or empty
    """
    unique_coords: Set[Tuple[float, float]] = set()
    
    print(f"[INFO] Loading polygons from {polygons_file.name}...")
    polygons = load_polygons(polygons_file)
    print(f"[INFO] Found {len(polygons)} valid polygons")
    
    print(f"[INFO] Sampling points inside polygons (grid resolution: {GRID_RESOLUTION}m)...")
    total_points = 0
    for i, polygon in enumerate(polygons):
        points = sample_points_inside_polygon(polygon, GRID_RESOLUTION)
        unique_coords.update(points)
        total_points += len(points)
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(polygons)} polygons... ({len(unique_coords)} unique coordinates so far)")
    
    if not unique_coords:
        raise ValueError("No coordinates found after sampling polygons")
    
    all_coords = list(unique_coords)
    all_coords.sort(key=lambda p: (p[0], p[1]))
    
    print(f"[INFO] Extracted {len(all_coords)} unique coordinates from road area")
    print(f"[INFO] Total points sampled: {total_points} (duplicates removed: {total_points - len(all_coords)})")
    
    return all_coords


def save_coordinates_to_json(coordinates: List[Tuple[float, float]], output_file: Path) -> None:
    """Save coordinates to JSON file in nested format.
    
    Args:
        coordinates: List of coordinate tuples
        output_file: Output file path
    """
    nested_coords = [[round(coord, COORDINATE_PRECISION) for coord in point] 
                     for point in coordinates]
    with open(output_file, 'w') as f:
        json.dump(nested_coords, f, indent=2)
    print(f"[INFO] Saved {len(coordinates)} coordinates to {output_file}")


def main() -> None:
    """Main execution function."""
    maps_dir = Path(__file__).parent.parent / 'maps'
    polygons_file = maps_dir / 'road_polygons_merged.json'
    output_file = maps_dir / 'all_road_coordinates.json'
    
    try:
        all_coords = extract_all_road_coordinates(polygons_file)
        save_coordinates_to_json(all_coords, output_file)
        print(f"[DONE] Successfully extracted all road area coordinates")
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] Failed to extract coordinates: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
