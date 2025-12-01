import json
import sys
import math
from xml.etree.ElementTree import Element, SubElement, ElementTree


def create_world_root():
    sdf = Element("sdf", version="1.8")
    world = SubElement(sdf, "world", name="bari_world")

    # Gravity
    gravity = SubElement(world, "gravity")
    gravity.text = "0 0 -9.81"

    # Physics (optional basic)
    physics = SubElement(world, "physics", name="default", type="ode")
    max_step_size = SubElement(physics, "max_step_size")
    max_step_size.text = "0.001"
    real_time_update_rate = SubElement(physics, "real_time_update_rate")
    real_time_update_rate.text = "1000"

    # Ground plane (optional, to have something under roads)
    model = SubElement(world, "model", name="ground_plane")
    static = SubElement(model, "static")
    static.text = "true"
    link = SubElement(model, "link", name="link")
    collision = SubElement(link, "collision", name="collision")
    geometry = SubElement(collision, "geometry")
    plane = SubElement(geometry, "plane")
    normal = SubElement(plane, "normal")
    normal.text = "0 0 1"
    size = SubElement(plane, "size")
    size.text = "1000 1000"
    visual = SubElement(link, "visual", name="visual")
    geometry_v = SubElement(visual, "geometry")
    plane_v = SubElement(geometry_v, "plane")
    normal_v = SubElement(plane_v, "normal")
    normal_v.text = "0 0 1"
    size_v = SubElement(plane_v, "size")
    size_v.text = "1000 1000"

    return sdf, world


def add_road_segment(world, seg_name, x_mid, y_mid, yaw, length, width, thickness=0.05):
    model = SubElement(world, "model", name=seg_name)

    static = SubElement(model, "static")
    static.text = "true"

    # pose: x y z roll pitch yaw
    pose = SubElement(model, "pose")
    pose.text = f"{x_mid} {y_mid} 0 {0} {0} {yaw}"

    link = SubElement(model, "link", name="link")

    # Collision
    collision = SubElement(link, "collision", name="collision")
    coll_geom = SubElement(collision, "geometry")
    box = SubElement(coll_geom, "box")
    size = SubElement(box, "size")
    size.text = f"{length} {width} {thickness}"

    # Visual
    visual = SubElement(link, "visual", name="visual")
    vis_geom = SubElement(visual, "geometry")
    box_v = SubElement(vis_geom, "box")
    size_v = SubElement(box_v, "size")
    size_v.text = f"{length} {width} {thickness}"

    material = SubElement(visual, "material")
    ambient = SubElement(material, "ambient")
    ambient.text = "0.2 0.2 0.2 1"
    diffuse = SubElement(material, "diffuse")
    diffuse.text = "0.3 0.3 0.3 1"


def main():
    if len(sys.argv) != 4:
        print("Usage: python build_sdf_roads.py <map_enu.json> <edges.json> <output.sdf>")
        sys.exit(1)

    map_enu_file = sys.argv[1]
    edges_file = sys.argv[2]
    output_sdf = sys.argv[3]

    print("Loading ENU map:", map_enu_file)
    with open(map_enu_file, "r") as f:
        map_data = json.load(f)

    node_coords = map_data["nodes_enu"]

    print("Loading edges:", edges_file)
    with open(edges_file, "r") as f:
        edges_data = json.load(f)

    sdf, world = create_world_root()

    print("Creating road segments in SDF...")

    seg_count = 0

    for way_id, data in edges_data.items():
        way_nodes = data["centerline_nodes"]
        width = data["width"]

        # Build segments from centerline nodes
        for i in range(len(way_nodes) - 1):
            nid1 = str(way_nodes[i])
            nid2 = str(way_nodes[i + 1])

            if nid1 not in node_coords or nid2 not in node_coords:
                continue

            x1, y1 = node_coords[nid1]
            x2, y2 = node_coords[nid2]

            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx*dx + dy*dy)
            if length < 0.1:
                continue  # skip tiny segments

            # midpoint
            x_mid = (x1 + x2) / 2.0
            y_mid = (y1 + y2) / 2.0

            # yaw from segment direction
            yaw = math.atan2(dy, dx)

            seg_name = f"road_{way_id}_seg_{i}"
            add_road_segment(world, seg_name, x_mid, y_mid, yaw, length, width)

            seg_count += 1

    print(f"Total road segments added: {seg_count}")
    print("Saving SDF to:", output_sdf)

    tree = ElementTree(sdf)
    tree.write(output_sdf, encoding="utf-8", xml_declaration=True)

    print("Done.")


if __name__ == "__main__":
    main()
