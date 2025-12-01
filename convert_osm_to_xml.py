import osmium
import sys
import xml.etree.ElementTree as ET

class RoadExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.nodes = {}
        self.ways = []

    def node(self, n):
        # Save nodes with coordinates
        self.nodes[n.id] = (n.location.lat, n.location.lon)

    def way(self, w):
        # Only accept real roads
        if 'highway' in w.tags:
            node_ids = [nd.ref for nd in w.nodes]

            # FIX: TagList must be iterated manually
            tags = {}
            for tag in w.tags:
                tags[tag.k] = tag.v

            self.ways.append({
                'id': w.id,
                'nodes': node_ids,
                'tags': tags
            })


def write_clean_xml(nodes, ways, output_xml):
    root = ET.Element("osm", version="0.6")

    # Write nodes
    for nid, (lat, lon) in nodes.items():
        ET.SubElement(root, "node", {
            "id": str(nid),
            "lat": str(lat),
            "lon": str(lon)
        })

    # Write ways (roads)
    for w in ways:
        way_el = ET.SubElement(root, "way", {"id": str(w["id"])})

        # Add node refs
        for nid in w["nodes"]:
            ET.SubElement(way_el, "nd", {"ref": str(nid)})

        # Add tags
        for k, v in w["tags"].items():
            ET.SubElement(way_el, "tag", {"k": k, "v": v})

    tree = ET.ElementTree(root)
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)


def main():
    if len(sys.argv) != 3:
        print("Usage: python convert_osm_to_xml.py <input.osm> <output.xml>")
        sys.exit(1)

    input_osm = sys.argv[1]
    output_xml = sys.argv[2]

    print("Reading OSM:", input_osm)
    handler = RoadExtractor()
    handler.apply_file(input_osm, locations=True)

    print("Writing cleaned XML:", output_xml)
    write_clean_xml(handler.nodes, handler.ways, output_xml)

    print("Done! Output saved to:", output_xml)


if __name__ == "__main__":
    main()
