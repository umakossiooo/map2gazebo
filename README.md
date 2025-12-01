python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

sudo apt-get install osmosis

chmod +x scripts/convert_osm_to_xml.py

python scripts/convert_osm_to_xml.py maps/map.osm maps/map.xml

chmod +x scripts/convert_xml_to_enu.py

python scripts/convert_xml_to_enu.py maps/map.xml maps/map.json auto