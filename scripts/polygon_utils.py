#!/usr/bin/env python3
"""Shared utilities for polygon operations."""

import json
from pathlib import Path
from typing import List
from shapely.geometry import Polygon


def load_polygons(polygons_file: Path) -> List[Polygon]:
    """Load and validate polygons from JSON file.
    
    Args:
        polygons_file: Path to road_polygons_merged.json
        
    Returns:
        List of valid Shapely Polygon objects
        
    Raises:
        ValueError: If no valid polygons are found
        FileNotFoundError: If file doesn't exist
    """
    if not polygons_file.exists():
        raise FileNotFoundError(f"Polygons file not found: {polygons_file}")
    
    with open(polygons_file, 'r') as f:
        data = json.load(f)
    
    polygons = []
    for road_data in data.values():
        for poly_coords in road_data.get('merged_polygons', []):
            if len(poly_coords) < 3:
                continue
            try:
                poly = Polygon(poly_coords)
                if not poly.is_valid or poly.is_empty:
                    # Try to fix invalid polygon
                    poly = poly.buffer(0)
                    if poly.is_empty:
                        continue
                polygons.append(poly)
            except Exception:
                continue
    
    if not polygons:
        raise ValueError("No valid polygons found in file")
    
    return polygons

