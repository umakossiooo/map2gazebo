import json
import sys
import math
import numpy as np

# Default widths (fallbacks)
DEFAULT_WIDTHS = {
    "motorway": 25.0,
    "trunk": 20.0,
    "primary": 12.0,
    "secondary": 10.0,
    "tertiary": 8.0,
    "unclassified": 7.0,
    "residential": 6.0,
    "service": 4.5,
}

LANE_WIDTH = 3.2  # meters per lane


def compute_width(tags):
    """Return width using Option A logic."""

    # A1: Direct width tag
    if "width" in tags:
        try:
            return float(tags["width"])
        except:
            pass

    # A2: Lanes tag
    if "lanes" in tags:
        try:
            lanes = int(tags["lanes"])
            return lanes * LANE_WIDTH
        except:
            pass

    # A3: Use highway default
    if "highway" in tags and tags["highway"] in DEFAULT_WIDTHS:
        return DEFAULT_WIDTHS[tags["highway"]]

    # A4: Unknown type → safe fallback
    return 6.0


def perpendicular_vector(p1, p2):
    """Compute a normalized perpendicular vector for segment p1→p2."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    # perpendicular vector (-dy, dx)
    px, py = -dy, dx
    length = math.sqrt(px*px + py*py)

    if length == 0:
        return np.array([0.0, 0.0])  # degenerate segment

    return np.array([px / length, py / length])


def compute_edges_for_way(node_coords, way_nodes, width):
    half = width / 2.0
    left_edge = []
    right_edge = []

    for i in range(len(way_nodes) - 1):
        n1 = node_coords[str(way_nodes[i])]
        n2 = node_coords[str(way_nodes[i+1])]

        p1 = np.array(n1)
        p2 = np.array(n2)

        perp = perpendicular_vector(p1, p2)

        left_edge.append((p1 + perp * half).tolist())
        right_edge.append((p1 - perp * half).tolist())

        # Add last point for final segment
        if i == len(way_nodes) - 2:
            left_edge.append((p2 + perp * half).tolist())
            right_edge.append((p2 - perp * half).tolist())

    return left_edge, right_edge


def main():
    if len(sys.argv) != 3:
        print("Usage: python compute_edges.py <map_enu.json> <edges.json>")
        sys.exit(1)

    input_json = sys.argv[1]
    output_json = sys.argv[2]

    print("Loading ENU map:", input_json)
    with open(input_json, "r") as f:
        data = json.load(f)

    node_coords = data["nodes_enu"]
    ways = data["ways"]

    edges_output = {}

    print("Computing edges for each road...")

    for way in ways:
        wid = str(way["id"])
        way_nodes = way["nodes"]
        tags = way["tags"]

        width = compute_width(tags)
        left_edge, right_edge = compute_edges_for_way(node_coords, way_nodes, width)

        edges_output[wid] = {
            "width": width,
            "centerline_nodes": way_nodes,
            "left_edge": left_edge,
            "right_edge": right_edge,
            "tags": tags
        }

    print("Saving:", output_json)
    with open(output_json, "w") as f:
        json.dump(edges_output, f, indent=4)

    print("Done! Left/right edges generated.")


if __name__ == "__main__":
    main()
