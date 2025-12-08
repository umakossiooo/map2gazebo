import osmium
import sys
import xml.etree.ElementTree as ET

class RoadExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.nodes = {}
        self.ways = {}       # Store ALL ways temporarily {id: {nodes:[], tags:{}}}
        self.relations = []  # Store building relations
        self.needed_way_ids = set() # Ways we must keep (roads + building parts)

    def node(self, n):
        self.nodes[n.id] = (n.location.lat, n.location.lon)

    def way(self, w):
        # Store way data
        tags = {tag.k: tag.v for tag in w.tags}
        self.ways[w.id] = {
            'id': w.id,
            'nodes': [nd.ref for nd in w.nodes],
            'tags': tags
        }
        
        # Keep if it is a road or a building itself
        if 'highway' in tags or 'building' in tags:
            self.needed_way_ids.add(w.id)

    def relation(self, r):
        # Keep if it is a building multipolygon
        if 'building' in r.tags and r.tags.get('type') == 'multipolygon':
            members = []
            for m in r.members:
                if m.type == 'w':
                    members.append({'ref': m.ref, 'role': m.role})
                    self.needed_way_ids.add(m.ref) # Mark member way as needed
            
            tags = {tag.k: tag.v for tag in r.tags}
            self.relations.append({
                'id': r.id,
                'members': members,
                'tags': tags
            })

def write_clean_xml(nodes, ways_dict, relations, needed_way_ids, output_xml):
    root = ET.Element("osm", version="0.6")

    # 1. Collect used node IDs from the needed ways
    used_node_ids = set()
    final_ways = []
    
    # Filter ways
    for wid in needed_way_ids:
        if wid in ways_dict:
            w = ways_dict[wid]
            final_ways.append(w)
            for nid in w['nodes']:
                used_node_ids.add(nid)
    
    # 2. Write Nodes
    for nid, (lat, lon) in nodes.items():
        if nid in used_node_ids:
            ET.SubElement(root, "node", {"id": str(nid), "lat": str(lat), "lon": str(lon)})

    # 3. Write Ways
    for w in final_ways:
        way_el = ET.SubElement(root, "way", {"id": str(w["id"])})
        for nid in w["nodes"]:
            ET.SubElement(way_el, "nd", {"ref": str(nid)})
        for k, v in w["tags"].items():
            ET.SubElement(way_el, "tag", {"k": k, "v": v})
            
    # 4. Write Relations
    for r in relations:
        rel_el = ET.SubElement(root, "relation", {"id": str(r["id"])})
        for m in r["members"]:
            ET.SubElement(rel_el, "member", {"type": "way", "ref": str(m["ref"]), "role": m["role"]})
        for k, v in r["tags"].items():
            ET.SubElement(rel_el, "tag", {"k": k, "v": v})

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

    print(f"Collected {len(handler.ways)} ways and {len(handler.relations)} relations.")
    print(f"Filtering down to {len(handler.needed_way_ids)} relevant ways...")

    write_clean_xml(handler.nodes, handler.ways, handler.relations, handler.needed_way_ids, output_xml)
    print("Done! Output saved to:", output_xml)

if __name__ == "__main__":
    main()
