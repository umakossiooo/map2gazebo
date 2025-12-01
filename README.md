python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

sudo apt-get install osmosis

chmod +x convert_osm_to_xml.py

python convert_osm_to_xml.py maps/map.osm xml_maps/map.xml
