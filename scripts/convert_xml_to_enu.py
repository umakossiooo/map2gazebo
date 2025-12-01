import sys
import json
import xml.etree.ElementTree as ET
from pyproj import Proj, Transformer

def load_osm_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    nodes = {}
    ways = []

    # Extract nodes
    for n in root.findall("node"):
        nid = int(n.attrib["id"])
        lat = float(n.attrib["lat"])
        lon = float(n.attrib["lon"])
        nodes[nid] = (lat, lon)

    # Extract ways
    for w in root.findall("way"):
        wid = int(w.attrib["id"])
        node_refs = [int(nd.attrib["ref"]) for nd in w.findall("nd")]

        tags = {}
        for tag in w.findall("tag"):
            tags[tag.attrib["k"]] = tag.attrib["v"]

        ways.append({
            "id": wid,
            "nodes": node_refs,
            "tags": tags
        })

    return nodes, ways


def convert_to_enu(nodes, origin_lat, origin_lon):
    # Set WGS84 → ENU transformer
    proj_lla = Proj(proj='latlong', datum='WGS84')
    proj_enu = Proj(proj='aeqd', lat_0=origin_lat, lon_0=origin_lon, datum='WGS84')
    transformer = Transformer.from_proj(proj_lla, proj_enu, always_xy=True)

    enu_nodes = {}

    for nid, (lat, lon) in nodes.items():
        x, y = transformer.transform(lon, lat)
        enu_nodes[nid] = [float(x), float(y)]

    return enu_nodes


def save_to_json(output_path, enu_nodes, ways):
    data = {
        "nodes_enu": enu_nodes,
        "ways": ways
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)

    print("Saved ENU map to:", output_path)


def main():
    if len(sys.argv) != 4:
        print("Usage: python convert_xml_to_enu.py <input.xml> <output.json> <origin_mode>")
        print("origin_mode options:")
        print("  auto   - use first node as the origin")
        print("  fixed  - manually set origin inside the script")
        sys.exit(1)

    xml_path = sys.argv[1]
    output_path = sys.argv[2]
    origin_mode = sys.argv[3]

    print("Loading XML:", xml_path)
    nodes, ways = load_osm_xml(xml_path)

    # Determine origin
    if origin_mode == "auto":
        first_lat, first_lon = list(nodes.values())[0]
        origin_lat = first_lat
        origin_lon = first_lon
        print(f"Using AUTO origin at lat={origin_lat}, lon={origin_lon}")
    else:
        # Set your custom origin here if needed
        origin_lat = 41.1200
        origin_lon = 16.8680
        print(f"Using FIXED origin at lat={origin_lat}, lon={origin_lon}")

    print("Converting nodes to ENU...")
    enu_nodes = convert_to_enu(nodes, origin_lat, origin_lon)

    print("Saving ENU file:", output_path)
    save_to_json(output_path, enu_nodes, ways)

    print("DONE.")


if __name__ == "__main__":
    main()
