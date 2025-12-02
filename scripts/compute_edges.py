import argparse
import json
import math
import numpy as np

# Width configuration (all in meters)
LANE_WIDTH = 3.2
WIDTH_BY_HIGHWAY = {
    "motorway": 18.0,
    "trunk": 15.0,
    "primary": 12.0,
    "secondary": 10.0,
    "tertiary": 8.0,
    "unclassified": 7.0,
    "residential": 6.0,
    "service": 5.0,
}
DEFAULT_ROAD_WIDTH = 6.5
MIN_ROAD_WIDTH = 4.0
MAX_ROAD_WIDTH = 18.0

ALLOWED_HIGHWAYS = set(WIDTH_BY_HIGHWAY.keys())


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


def clamp_width(width):
    return max(MIN_ROAD_WIDTH, min(MAX_ROAD_WIDTH, width))


def compute_width(tags):
    if not tags:
        return DEFAULT_ROAD_WIDTH

    if "width" in tags:
        try:
            return clamp_width(float(tags["width"]))
        except Exception:
            pass

    if "lanes" in tags:
        try:
            lanes = max(1, int(tags["lanes"]))
            return clamp_width(lanes * LANE_WIDTH)
        except Exception:
            pass

    highway = tags.get("highway")
    if highway in WIDTH_BY_HIGHWAY:
        return WIDTH_BY_HIGHWAY[highway]

    return DEFAULT_ROAD_WIDTH


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute left/right edges for every drivable road."
    )
    parser.add_argument("map_json", help="Input ENU-converted map (maps/map.json)")
    parser.add_argument("edges_json", help="Output file for edge data")
    return parser.parse_args()


def main():
    args = parse_args()

    input_json = args.map_json
    output_json = args.edges_json

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
        highway_type = tags.get("highway")
        if highway_type not in ALLOWED_HIGHWAYS:
            continue

        width = compute_width(tags)
        left_edge, right_edge = compute_edges_for_way(node_coords, way_nodes, width)

        centerline_points = []
        for node_id in way_nodes:
            coord = node_coords.get(str(node_id))
            if coord is None:
                continue
            centerline_points.append(coord)

        edges_output[wid] = {
            "width": width,
            "centerline_nodes": way_nodes,
            "left_edge": left_edge,
            "right_edge": right_edge,
            "centerline_points": centerline_points,
            "tags": tags
        }

    print("Saving:", output_json)
    with open(output_json, "w") as f:
        json.dump(edges_output, f, indent=4)

    print("Done! Left/right edges generated.")


if __name__ == "__main__":
    main()
