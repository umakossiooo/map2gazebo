import json
import sys

from shapely.geometry import LineString


def build_polygon(left_edge, right_edge):
    """Fallback: combine left edge with reversed right edge."""
    polygon = []

    for pt in left_edge:
        polygon.append(pt)

    for pt in reversed(right_edge):
        polygon.append(pt)

    if polygon and polygon[0] != polygon[-1]:
        polygon.append(polygon[0])

    return polygon


def build_polygon_from_centerline(centerline_points, width):
    if not centerline_points or len(centerline_points) < 2:
        return None

    try:
        line = LineString(centerline_points)
    except Exception as exc:
        print(f"[WARN] Could not build LineString ({exc}); falling back to offsets")
        return None

    if line.is_empty:
        return None

    half_width = width / 2.0
    road_poly = line.buffer(half_width, cap_style=2, join_style=2, mitre_limit=5.0)

    if road_poly.is_empty:
        return None

    coords = list(road_poly.exterior.coords)
    return coords if coords else None


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
    buffered_count = 0
    fallback_count = 0

    for wid, data in edges.items():
        left_edge = data["left_edge"]
        right_edge = data["right_edge"]
        width = data["width"]
        tags = data["tags"]
        centerline_points = data.get("centerline_points", [])

        polygon = build_polygon_from_centerline(centerline_points, width)

        if polygon is None:
            polygon = build_polygon(left_edge, right_edge)
            fallback_count += 1
        else:
            buffered_count += 1

        polygons[wid] = {
            "polygon": polygon,
            "width": width,
            "tags": tags
        }

    print(f"  [INFO] Buffered polygons: {buffered_count}")
    print(f"  [INFO] Fallback polygons: {fallback_count}")

    print("Saving:", output_file)
    with open(output_file, "w") as f:
        json.dump(polygons, f, indent=4)

    print("Done! Road polygons generated.")


if __name__ == "__main__":
    main()
