python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

sudo apt-get install osmosis

chmod +x scripts/convert_osm_to_xml.py

python scripts/convert_osm_to_xml.py maps/map.osm maps/map.xml

chmod +x scripts/convert_xml_to_enu.py

python scripts/convert_xml_to_enu.py maps/map.xml maps/map.json auto

chmod +x scripts/compute_edges.py

python scripts/compute_edges.py maps/map.json maps/edges.json

chmod +x scripts/compute_polygons.py

python scripts/compute_polygons.py maps/edges.json maps/road_polygons.json

chmod +x scripts/merge_polygons.py

python scripts/merge_polygons.py maps/road_polygons.json maps/road_polygons_merged.json

chmod +x scripts/build_sdf_roads.py

python scripts/build_sdf_roads.py maps/road_polygons_merged.json worlds/bari_world.sdf
