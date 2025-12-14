#!/usr/bin/env python3
"""
build_sdf_sidewalks.py

Generates an OBJ and SDF model for sidewalks from merged polygons.
"""

import argparse
import json
import sys
import math
import shutil
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import triangulate as shapely_triangulate


def triangulate_polygon(poly):
    """Triangula polígonos cóncavos usando shapely.ops.triangulate."""
    if isinstance(poly, Polygon):
        shapely_poly = poly
    else:
        if len(poly) < 3:
            return []
        try:
            shapely_poly = Polygon(poly)
        except Exception as exc:
            print(f"[WARN] Could not build shapely Polygon for triangulation ({exc})")
            return []

    if shapely_poly.is_empty:
        return []

    if not shapely_poly.is_valid:
        shapely_poly = shapely_poly.buffer(0)
        if shapely_poly.is_empty:
            return []

    triangles = []
    for tri in shapely_triangulate(shapely_poly):
        if not shapely_poly.contains(tri.representative_point()):
            continue

        coords = list(tri.exterior.coords)
        if len(coords) < 3:
            continue

        triangles.append([coords[0], coords[1], coords[2]])

    return triangles


def compute_normal(p1, p2, p3):
    """Normal unitaria hacia +Z (or generic)."""
    ux, uy, uz = p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]
    vx, vy, vz = p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2]

    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx

    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0:
        return 0.0, 0.0, 1.0

    nx /= length
    ny /= length
    nz /= length

    return nx, ny, nz


def add_quad(p1, p2, p3, p4, vertices, normals, faces, v_idx, n_idx):
    """Adds a quad (2 triangles) defined by 4 points (CCW or CW)."""
    # Triangle 1: p1, p2, p3
    nx, ny, nz = compute_normal(p1, p2, p3)
    
    vertices.append(f"v {p1[0]} {p1[1]} {p1[2]}\n")
    vertices.append(f"v {p2[0]} {p2[1]} {p2[2]}\n")
    vertices.append(f"v {p3[0]} {p3[1]} {p3[2]}\n")
    
    normals.append(f"vn {nx} {ny} {nz}\n")
    normals.append(f"vn {nx} {ny} {nz}\n")
    normals.append(f"vn {nx} {ny} {nz}\n")
    
    faces.append(f"f {v_idx}//{n_idx} {v_idx+1}//{n_idx+1} {v_idx+2}//{n_idx+2}\n")
    v_idx += 3
    n_idx += 3
    
    # Triangle 2: p1, p3, p4
    nx, ny, nz = compute_normal(p1, p3, p4)
    
    vertices.append(f"v {p1[0]} {p1[1]} {p1[2]}\n")
    vertices.append(f"v {p3[0]} {p3[1]} {p3[2]}\n")
    vertices.append(f"v {p4[0]} {p4[1]} {p4[2]}\n")
    
    normals.append(f"vn {nx} {ny} {nz}\n")
    normals.append(f"vn {nx} {ny} {nz}\n")
    normals.append(f"vn {nx} {ny} {nz}\n")
    
    faces.append(f"f {v_idx}//{n_idx} {v_idx+1}//{n_idx+1} {v_idx+2}//{n_idx+2}\n")
    v_idx += 3
    n_idx += 3
    
    return v_idx, n_idx


def build_obj_from_polygons(polygons, output_obj_path: Path):
    print("[INFO] Building sidewalks OBJ mesh (Top + Walls)...")

    vertices = []
    normals = []
    faces = []

    v_idx = 1
    n_idx = 1
    Z_TOP = 0.15
    Z_BOTTOM = 0.05 # Match road height

    for poly in polygons:
        if isinstance(poly, Polygon):
            if poly.is_empty or poly.area == 0:
                continue
        else:
            if len(poly) < 3:
                continue

        # 1. Build Top Face (Triangulated)
        tris = triangulate_polygon(poly)
        for tri in tris:
            (x1, y1) = tri[0]
            (x2, y2) = tri[1]
            (x3, y3) = tri[2]

            p1 = (x1, y1, Z_TOP)
            p2 = (x2, y2, Z_TOP)
            p3 = (x3, y3, Z_TOP)

            nx, ny, nz = compute_normal(p1, p2, p3)
            # Force up normal for top face
            if nz < 0: nx, ny, nz = -nx, -ny, -nz

            vertices.append(f"v {p1[0]} {p1[1]} {p1[2]}\n")
            vertices.append(f"v {p2[0]} {p2[1]} {p2[2]}\n")
            vertices.append(f"v {p3[0]} {p3[1]} {p3[2]}\n")

            normals.append(f"vn {nx} {ny} {nz}\n")
            normals.append(f"vn {nx} {ny} {nz}\n")
            normals.append(f"vn {nx} {ny} {nz}\n")

            faces.append(
                f"f {v_idx}//{n_idx} {v_idx+1}//{n_idx+1} {v_idx+2}//{n_idx+2}\n"
            )

            v_idx += 3
            n_idx += 3
            
        # 2. Build Side Walls (Exterior)
        coords = list(poly.exterior.coords)
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i+1]
            
            # Wall Quad: Top-Edge to Bottom-Edge
            # We want vertical face.
            # V1_top, V2_top, V2_bottom, V1_bottom
            v1t = (p1[0], p1[1], Z_TOP)
            v2t = (p2[0], p2[1], Z_TOP)
            v2b = (p2[0], p2[1], Z_BOTTOM)
            v1b = (p1[0], p1[1], Z_BOTTOM)
            
            v_idx, n_idx = add_quad(v1t, v2t, v2b, v1b, vertices, normals, faces, v_idx, n_idx)

        # 3. Build Side Walls (Interiors / Holes)
        for interior in poly.interiors:
            coords = list(interior.coords)
            for i in range(len(coords) - 1):
                p1 = coords[i]
                p2 = coords[i+1]
                
                v1t = (p1[0], p1[1], Z_TOP)
                v2t = (p2[0], p2[1], Z_TOP)
                v2b = (p2[0], p2[1], Z_BOTTOM)
                v1b = (p1[0], p1[1], Z_BOTTOM)
                
                v_idx, n_idx = add_quad(v1t, v2t, v2b, v1b, vertices, normals, faces, v_idx, n_idx)

    output_obj_path.parent.mkdir(parents=True, exist_ok=True)
    with output_obj_path.open("w") as obj:
        obj.writelines(vertices)
        obj.writelines(normals)
        obj.writelines(faces)

    print(f"[OK] OBJ mesh created at: {output_obj_path}")


def create_model_sdf(model_dir: Path, mesh_rel: str):
    sdf_path = model_dir / "model.sdf"

    sdf_xml = f"""<?xml version="1.6"?>
<sdf version="1.8">
  <model name="sidewalks_mesh">
    <static>true</static>
    <link name="sidewalk_link">
      <visual name="vis">
        <geometry>
          <mesh>
            <uri>model://sidewalks_mesh/{mesh_rel}</uri>
          </mesh>
        </geometry>
        <material>
          <diffuse>0.6 0.6 0.6 1</diffuse>
          <ambient>0.5 0.5 0.5 1</ambient>
        </material>
      </visual>
      <collision name="col">
        <geometry>
          <mesh>
            <uri>model://sidewalks_mesh/{mesh_rel}</uri>
          </mesh>
        </geometry>
      </collision>
    </link>
  </model>
</sdf>
"""
    model_dir.mkdir(parents=True, exist_ok=True)
    with sdf_path.open("w") as f:
        f.write(sdf_xml)

    print(f"[OK] model.sdf created: {sdf_path}")


def create_model_config(model_dir: Path):
    cfg_path = model_dir / "model.config"

    cfg_xml = """<?xml version="1.0"?>
<model>
  <name>sidewalks_mesh</name>
  <version>1.0</version>
  <sdf version="1.8">model.sdf</sdf>
  <author><name>map2gazebo</name></author>
  <description>Sidewalk mesh generated from OSM data</description>
</model>
"""
    with cfg_path.open("w") as f:
        f.write(cfg_xml)

    print(f"[OK] model.config created: {cfg_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_sdf_sidewalks.py <input_sidewalks_merged.json>")
        sys.exit(1)

    json_in = Path(sys.argv[1])
    
    print(f"[INFO] Loading merged sidewalk polygons from: {json_in}")
    with json_in.open("r") as f:
        data = json.load(f)

    polygons = []
    for entry in data.values():
        merged_polys = entry.get("merged_polygons", [])
        for coords in merged_polys:
            if len(coords) < 3:
                continue
            try:
                poly = Polygon(coords)
            except Exception as exc:
                continue

            if poly.is_empty:
                continue

            if not poly.is_valid:
                poly = poly.buffer(0)
                if poly.is_empty:
                    continue

            polygons.append(poly)

    if not polygons:
        print("[ERROR] No polygons found.")
        sys.exit(1)

    model_dir = Path("worlds/models/sidewalks_mesh")
    mesh_rel = "meshes/sidewalks_mesh.obj"
    mesh_out = model_dir / mesh_rel

    if model_dir.exists():
        shutil.rmtree(model_dir)

    build_obj_from_polygons(polygons, mesh_out)
    create_model_sdf(model_dir, mesh_rel)
    create_model_config(model_dir)

    print("[DONE] Sidewalks model generated.")


if __name__ == "__main__":
    main()

