#!/usr/bin/env python3
"""Extract random route goals from road area (polygons) and save to JSON file."""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import List, Tuple
from shapely.geometry import Polygon, Point
from polygon_utils import load_polygons

# Constants
NUM_RANDOM_COORDINATES = 15
DUPLICATE_TOLERANCE_SQ = 1.0  # 1 meter squared
SPAWN_REF = (0.0, -100.0)
MAX_SAMPLING_ATTEMPTS = 100
ROUTE_GOAL_PRECISION = 2


def sample_point_from_polygon(polygon: Polygon) -> Tuple[float, float]:
    """Sample a single random point from inside a polygon.
    
    Args:
        polygon: Shapely Polygon to sample from
        
    Returns:
        Coordinate tuple (x, y)
    """
    minx, miny, maxx, maxy = polygon.bounds
    
    for _ in range(MAX_SAMPLING_ATTEMPTS):
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        point = Point(x, y)
        if polygon.contains(point) or polygon.touches(point):
            return (round(x, ROUTE_GOAL_PRECISION), round(y, ROUTE_GOAL_PRECISION))
    
    # Fallback: return centroid if sampling fails
    centroid = polygon.centroid
    return (round(centroid.x, ROUTE_GOAL_PRECISION), 
            round(centroid.y, ROUTE_GOAL_PRECISION))


def is_duplicate(point: Tuple[float, float], existing: List[Tuple[float, float]]) -> bool:
    """Check if point is duplicate (within tolerance) of existing points.
    
    Args:
        point: Point to check
        existing: List of existing points
        
    Returns:
        True if point is a duplicate, False otherwise
    """
    for existing_point in existing:
        dx = point[0] - existing_point[0]
        dy = point[1] - existing_point[1]
        if dx * dx + dy * dy < DUPLICATE_TOLERANCE_SQ:
            return True
    return False


def extract_route_goals(polygons_file: Path, num_routes: int) -> List[Tuple[float, float]]:
    """Extract random route goals from road polygons.
    
    Args:
        polygons_file: Path to road_polygons_merged.json
        num_routes: Number of route goals to extract
        
    Returns:
        List of coordinate tuples sorted by distance from spawn reference
        
    Raises:
        ValueError: If num_routes is less than 1 or no valid polygons are found.
    """
    if num_routes < 1:
        raise ValueError("Number of routes must be at least 1.")

    polygons = load_polygons(polygons_file)
    random.shuffle(polygons)
    
    points = []
    attempts = 0
    max_attempts = num_routes * 100
    
    while len(points) < num_routes and attempts < max_attempts:
        attempts += 1
        polygon = random.choice(polygons)
        point = sample_point_from_polygon(polygon)
        
        if not is_duplicate(point, points):
            points.append(point)
    
    if len(points) < num_routes:
        print(f"[WARN] Only generated {len(points)} unique points (requested {num_routes})")
    
    # Sort by distance from spawn area
    points.sort(key=lambda p: (p[0] - SPAWN_REF[0])**2 + (p[1] - SPAWN_REF[1])**2)
    
    return points[:num_routes]


def save_coordinates_to_json(coordinates: List[Tuple[float, float]], output_file: Path) -> None:
    """Save coordinates to JSON file in flattened format.
    
    Args:
        coordinates: List of coordinate tuples
        output_file: Output file path
    """
    flat_coords = [round(coord, ROUTE_GOAL_PRECISION) 
                   for point in coordinates for coord in point]
    with open(output_file, 'w') as f:
        json.dump(flat_coords, f, indent=2)


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Extract random route goals from road network',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract 15 random route goals (default)
  python3 extract_route_goals.py
  
  # Extract custom number of random route goals
  python3 extract_route_goals.py 20
        """
    )
    parser.add_argument(
        'num_routes',
        nargs='?',
        type=int,
        default=NUM_RANDOM_COORDINATES,
        help=f'Number of random route goals to extract (default: {NUM_RANDOM_COORDINATES})'
    )
    
    args = parser.parse_args()
    
    maps_dir = Path(__file__).parent.parent / 'maps'
    polygons_file = maps_dir / 'road_polygons_merged.json'
    output_file = maps_dir / 'route_goals.json'
    
    try:
        print(f"[INFO] Extracting {args.num_routes} random route goals...")
        route_goals = extract_route_goals(polygons_file, args.num_routes)
        print(f"[INFO] Generated {len(route_goals)} route goals")
        
        save_coordinates_to_json(route_goals, output_file)
        print(f"[INFO] Saved route goals to {output_file}")
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] Failed to extract route goals: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
