import json
import sys

def build_polygon(left_edge, right_edge):
    """
    Combine left edge with reversed right edge 
    to form a closed polygon.
    """
    polygon = []

    # Add left edge points
    for pt in left_edge:
        polygon.append(pt)

    # Add right edge points reversed
    for pt in reversed(right_edge):
        polygon.append(pt)

    # Close polygon explicitly
    if polygon[0] != polygon[-1]:
        polygon.append(polygon[0])

    return polygon


def main():
    if len(sys.argv) != 3:
        print("Usage: python compute_polygons.py <edges.json> <polygons.json>")
        sys.exit(1)

    edges_file = sys.argv[1]
    output_file = sys.argv[2]

    print("Loading edges:", edges_file)
    with open(edges_file, "r") as f:
        edges = json.load(f)

    polygons = {}

    print("Building polygons...")

    for wid, data in edges.items():
        left_edge = data["left_edge"]
        right_edge = data["right_edge"]
        width = data["width"]
        tags = data["tags"]

        polygon = build_polygon(left_edge, right_edge)

        polygons[wid] = {
            "polygon": polygon,
            "width": width,
            "tags": tags
        }

    print("Saving:", output_file)
    with open(output_file, "w") as f:
        json.dump(polygons, f, indent=4)

    print("Done! Road polygons generated.")


if __name__ == "__main__":
    main()
