#!/usr/bin/env python3
"""
build_sdf_buildings.py

Generates a 3D OBJ mesh and Gazebo model for buildings.
Crucially, it subtracts the road polygons from the building footprints
to ensure no overlap, without affecting the road coordinate extraction pipeline.
"""

import sys
import json
import math
import shutil
import random
from pathlib import Path

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union, linemerge, polygonize
from shapely.strtree import STRtree

def compute_normal(p1, p2, p3):
    ux, uy, uz = p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]
    vx, vy, vz = p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = math.sqrt(nx*nx + ny*ny + nz*nz)
    if length > 0:
        return nx/length, ny/length, nz/length
    return 0, 0, 1

def build_buildings_obj(buildings_polys, output_obj_path):
    print(f"[INFO] Building OBJ for {len(buildings_polys)} buildings...")
    
    vertices = []
    normals = []
    faces = []
    v_idx = 1
    
    for poly, height in buildings_polys:
        if poly.is_empty: continue
        
        # Handle MultiPolygons (which might result from subtraction)
        if isinstance(poly, MultiPolygon):
            parts = poly.geoms
        else:
            parts = [poly]
            
        for part in parts:
            # 1. Walls
            exterior = list(part.exterior.coords)
            # Ensure correct winding (Counter-Clockwise for exterior)
            if not part.exterior.is_ccw:
                 exterior.reverse()

            for i in range(len(exterior) - 1):
                p1 = exterior[i]
                p2 = exterior[i+1]
                
                # Wall quad vertices: BL, BR, TR, TL
                v_bl = (p1[0], p1[1], 0.0)
                v_br = (p2[0], p2[1], 0.0)
                v_tr = (p2[0], p2[1], height)
                v_tl = (p1[0], p1[1], height)
                
                # Check for zero-length edge
                if p1 == p2: continue

                # Add vertices
                base_idx = len(vertices)
                for v in [v_bl, v_br, v_tr, v_tl]:
                    vertices.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
                
                # Wall Normal
                nx, ny, nz = compute_normal(v_bl, v_br, v_tl)
                normals.append(f"vn {nx:.4f} {ny:.4f} {nz:.4f}\n")
                
                # Faces (Double-sided to prevent invisibility)
                # Outer side
                faces.append(f"f {v_idx}//{len(normals)} {v_idx+1}//{len(normals)} {v_idx+2}//{len(normals)}\n")
                faces.append(f"f {v_idx}//{len(normals)} {v_idx+2}//{len(normals)} {v_idx+3}//{len(normals)}\n")
                
                # Inner side (flipped normal) - cheap double-sided rendering
                # Just reuse vertices but flip winding order
                faces.append(f"f {v_idx}//{len(normals)} {v_idx+2}//{len(normals)} {v_idx+1}//{len(normals)}\n")
                faces.append(f"f {v_idx}//{len(normals)} {v_idx+3}//{len(normals)} {v_idx+2}//{len(normals)}\n")

                v_idx += 4
            
            # Handle Interiors (Holes)
            for interior in part.interiors:
                coords = list(interior.coords)
                # Ensure correct winding (Clockwise for holes)
                # Shapely usually handles this, but good to be explicit
                # We render hole walls similarly
                for i in range(len(coords) - 1):
                    p1 = coords[i]
                    p2 = coords[i+1]
                    
                    v_bl = (p1[0], p1[1], 0.0)
                    v_br = (p2[0], p2[1], 0.0)
                    v_tr = (p2[0], p2[1], height)
                    v_tl = (p1[0], p1[1], height)

                    if p1 == p2: continue

                    for v in [v_bl, v_br, v_tr, v_tl]:
                        vertices.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
                    
                    nx, ny, nz = compute_normal(v_bl, v_br, v_tl)
                    normals.append(f"vn {nx:.4f} {ny:.4f} {nz:.4f}\n")
                    
                    faces.append(f"f {v_idx}//{len(normals)} {v_idx+1}//{len(normals)} {v_idx+2}//{len(normals)}\n")
                    faces.append(f"f {v_idx}//{len(normals)} {v_idx+2}//{len(normals)} {v_idx+3}//{len(normals)}\n")
                    
                    # Double sided
                    faces.append(f"f {v_idx}//{len(normals)} {v_idx+2}//{len(normals)} {v_idx+1}//{len(normals)}\n")
                    faces.append(f"f {v_idx}//{len(normals)} {v_idx+3}//{len(normals)} {v_idx+2}//{len(normals)}\n")
                    
                    v_idx += 4

            # 2. Roof (Simple triangulation)
            try:
                from shapely.ops import triangulate
                # Filter triangles to keep only those inside the building footprint
                tris = [t for t in triangulate(part) if part.contains(t.representative_point())]
                
                nx, ny, nz = 0.0, 0.0, 1.0 # Upward normal
                normals.append(f"vn {nx:.4f} {ny:.4f} {nz:.4f}\n")
                n_idx_top = len(normals)
                
                for tri in tris:
                    coords = list(tri.exterior.coords)[0:3]
                    # Ensure Counter-Clockwise winding
                    x1, y1 = coords[0]
                    x2, y2 = coords[1]
                    x3, y3 = coords[2]
                    if ((x2-x1)*(y3-y1) - (x3-x1)*(y2-y1)) < 0:
                        coords = [coords[0], coords[2], coords[1]]
                        
                    for x, y in coords:
                        vertices.append(f"v {x:.4f} {y:.4f} {height:.4f}\n")
                    
                    faces.append(f"f {v_idx}//{n_idx_top} {v_idx+1}//{n_idx_top} {v_idx+2}//{n_idx_top}\n")
                    v_idx += 3
            except Exception as e:
                pass

    output_obj_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_obj_path, "w") as f:
        f.writelines(vertices)
        f.writelines(normals)
        f.writelines(faces)

def create_model_files(model_dir, mesh_rel):
    config_xml = """<?xml version="1.0"?>
<model>
  <name>buildings_mesh</name>
  <version>1.0</version>
  <sdf version="1.8">model.sdf</sdf>
  <author><name>map2gazebo</name></author>
  <description>Generated buildings mesh</description>
</model>
"""
    sdf_xml = f"""<?xml version="1.6"?>
<sdf version="1.8">
  <model name="buildings_mesh">
    <static>true</static>
    <link name="link">
      <visual name="visual">
        <geometry>
          <mesh><uri>model://buildings_mesh/{mesh_rel}</uri></mesh>
        </geometry>
        <material>
          <diffuse>0.6 0.6 0.65 1</diffuse>
          <ambient>0.4 0.4 0.45 1</ambient>
        </material>
      </visual>
      <collision name="collision">
        <geometry>
          <mesh><uri>model://buildings_mesh/{mesh_rel}</uri></mesh>
        </geometry>
      </collision>
    </link>
  </model>
</sdf>
"""
    with open(model_dir / "model.config", "w") as f:
        f.write(config_xml)
    with open(model_dir / "model.sdf", "w") as f:
        f.write(sdf_xml)

def main():
    if len(sys.argv) < 3:
        print("Usage: python build_sdf_buildings.py <map.json> <road_polygons_merged.json>")
        sys.exit(1)
        
    map_json_path = Path(sys.argv[1])
    roads_json_path = Path(sys.argv[2])
    model_dir = Path("worlds/models/buildings_mesh")
    
    # 1. Load Road Polygons (to subtract later)
    print("[INFO] Loading road polygons...")
    road_polys = []
    with open(roads_json_path, "r") as f:
        roads_data = json.load(f)
        for entry in roads_data.values():
            for coords in entry.get("merged_polygons", []):
                if len(coords) >= 3:
                    road_polys.append(Polygon(coords).buffer(0))
    
    # STRtree for fast intersection checks
    if road_polys:
        road_tree = STRtree(road_polys)
    else:
        road_tree = None
        print("[WARN] No road polygons found. Buildings will not be clipped.")
    
    # 2. Load Buildings
    print("[INFO] Loading buildings from map...")
    with open(map_json_path, "r") as f:
        map_data = json.load(f)
    
    nodes_enu = map_data["nodes_enu"]
    final_buildings = []
    
    # --- Process WAYS (Simple Polygons) ---
    for w in map_data["ways"]:
        if "building" not in w["tags"]:
            continue
            
        coords = [nodes_enu[str(nid)] for nid in w["nodes"] if str(nid) in nodes_enu]
        if len(coords) < 3: continue
            
        poly = Polygon(coords).buffer(0)
        if not poly.is_valid or poly.is_empty: continue
        
        # Determine Height
        height = 10.0 + random.uniform(-2, 5)
        if "height" in w["tags"]:
            try: height = float(w["tags"]["height"])
            except: pass
        elif "building:levels" in w["tags"]:
             try: height = float(w["tags"]["building:levels"]) * 3.5
             except: pass

        final_buildings.append((poly, height))
        
    # --- Process RELATIONS (Complex Polygons / Multipolygons) ---
    way_map = {w["id"]: w for w in map_data["ways"]} # Quick lookup
    
    for r in map_data.get("relations", []):
        if "building" not in r["tags"]: continue
        
        # Collect member lines
        lines = []
        for m in r["members"]:
            wid = m["ref"]
            if wid in way_map:
                w = way_map[wid]
                coords = [nodes_enu[str(nid)] for nid in w["nodes"] if str(nid) in nodes_enu]
                if len(coords) > 1:
                    lines.append(coords)
        
        if not lines: continue
        
        # Reconstruct Polygon from lines
        try:
            merged = linemerge(lines)
            polys = list(polygonize(merged))
            if not polys: continue
            
            # Union all parts (simple approach for multipolygon)
            poly = unary_union(polys).buffer(0)
            
            # Determine Height (Same logic)
            height = 10.0 + random.uniform(-2, 5)
            if "height" in r["tags"]:
                try: height = float(r["tags"]["height"])
                except: pass
            elif "building:levels" in r["tags"]:
                 try: height = float(r["tags"]["building:levels"]) * 3.5
                 except: pass
            
            final_buildings.append((poly, height))
            
        except Exception as e:
            print(f"[WARN] Failed to process relation {r['id']}: {e}")
            pass

    # 3. Post-process: Subtract overlapping roads from ALL collected buildings
    print(f"[INFO] Processing {len(final_buildings)} potential building footprints...")
    processed_buildings = []
    
    for poly, height in final_buildings:
         if road_tree:
            intersecting_indices = road_tree.query(poly)
            if len(intersecting_indices) > 0:
                nearby_roads = [road_polys[i] for i in intersecting_indices]
                roads_union = unary_union(nearby_roads)
                try:
                    poly = poly.difference(roads_union)
                except Exception:
                    continue
        
         if not poly.is_empty:
             processed_buildings.append((poly, height))

    print(f"[INFO] Final count: {len(processed_buildings)} buildings after road subtraction.")

    # 5. Generate Mesh
    if model_dir.exists(): shutil.rmtree(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    mesh_rel = "meshes/buildings.obj"
    build_buildings_obj(processed_buildings, model_dir / mesh_rel)
    create_model_files(model_dir, mesh_rel)
    
    print("[DONE] Buildings generated in worlds/models/buildings_mesh")

if __name__ == "__main__":
    main()
