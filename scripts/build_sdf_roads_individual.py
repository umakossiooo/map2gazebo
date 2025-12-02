#!/usr/bin/env python3
"""
build_sdf_roads_individual.py

Genera un mesh OBJ y un mundo SDF a partir de TODOS los polígonos de calles
de maps/road_polygons_merged.json, triangulando cada polígono de forma
individual para mantener la forma original de cada calle.

Uso:
  python scripts/build_sdf_roads_individual.py maps/road_polygons_merged.json worlds/map.sdf
"""

import argparse
import json
import sys
import math
import shutil
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import triangulate as shapely_triangulate


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
ACKERMANN_PROJECT_DIR = REPO_ROOT.parent / "ackermann-vehicle-gzsim-ros2"
ACKERMANN_WORLD_PATH = ACKERMANN_PROJECT_DIR / "saye_description/worlds/bari_world.sdf"


# ================================================================
# TRIANGULACIÓN (con Shapely para soportar formas cóncavas)
# ================================================================

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
            print("[WARN] Polygon became empty after buffer(0) fix; skipping")
            return []

    triangles = []
    for tri in shapely_triangulate(shapely_poly):
        # representative_point always inside triangle, good for contains check
        if not shapely_poly.contains(tri.representative_point()):
            continue

        coords = list(tri.exterior.coords)
        if len(coords) < 3:
            continue

        # exterior coords are closed, so ignore last vertex
        triangles.append([coords[0], coords[1], coords[2]])

    return triangles


# ================================================================
# NORMALES
# ================================================================

def compute_normal(p1, p2, p3):
    """Normal unitaria hacia +Z."""
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

    # Aseguramos que miren hacia arriba
    if nz < 0:
        nx, ny, nz = -nx, -ny, -nz

    return nx, ny, nz


# ================================================================
# CONSTRUCCIÓN DE OBJ
# ================================================================

def build_obj_from_polygons(polygons, output_obj_path: Path):
    """Acepta secuencias de puntos o instancias de shapely.geometry.Polygon."""
    print("[INFO] Building roads OBJ mesh with one triangulation per street polygon...")

    vertices = []
    normals = []
    faces = []

    v_idx = 1
    n_idx = 1
    Z_ROAD = 0.05  # un poco por encima del ground_plane

    for poly in polygons:
        if isinstance(poly, Polygon):
            if poly.is_empty or poly.area == 0:
                continue
        else:
            if len(poly) < 3:
                continue

        tris = triangulate_polygon(poly)

        for tri in tris:
            (x1, y1) = tri[0]
            (x2, y2) = tri[1]
            (x3, y3) = tri[2]

            p1 = (x1, y1, Z_ROAD)
            p2 = (x2, y2, Z_ROAD)
            p3 = (x3, y3, Z_ROAD)

            nx, ny, nz = compute_normal(p1, p2, p3)

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

    output_obj_path.parent.mkdir(parents=True, exist_ok=True)
    with output_obj_path.open("w") as obj:
        obj.writelines(vertices)
        obj.writelines(normals)
        obj.writelines(faces)

    print(f"[OK] OBJ mesh created at: {output_obj_path}")
    print(f"     Vertices: {len(vertices)}")
    print(f"     Normals : {len(normals)}")
    print(f"     Faces   : {len(faces)}")


# ================================================================
# model.sdf y model.config
# ================================================================

def create_model_sdf(model_dir: Path, mesh_rel: str):
    sdf_path = model_dir / "model.sdf"

    sdf_xml = f"""<?xml version="1.6"?>
<sdf version="1.8">
  <model name="roads_mesh">
    <static>true</static>
    <link name="road_link">
      <visual name="vis">
        <geometry>
          <mesh>
            <uri>model://roads_mesh/{mesh_rel}</uri>
          </mesh>
        </geometry>
        <material>
          <diffuse>0.4 0.4 0.4 1</diffuse>
          <ambient>0.3 0.3 0.3 1</ambient>
        </material>
      </visual>
      <collision name="col">
        <geometry>
          <mesh>
            <uri>model://roads_mesh/{mesh_rel}</uri>
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
  <name>roads_mesh</name>
  <version>1.0</version>
  <sdf version="1.8">model.sdf</sdf>
  <author><name>map2gazebo</name></author>
  <description>Road mesh with one triangulation per street polygon</description>
</model>
"""
    with cfg_path.open("w") as f:
        f.write(cfg_xml)

    print(f"[OK] model.config created: {cfg_path}")


# ================================================================
# WORLD SDF
# ================================================================
def create_world_sdf(output_world_path: Path, world_name: str):
    world_xml = """<?xml version="1.6"?>
<sdf version="1.8">
  <world name="{world_name}">

    <gravity>0 0 -9.81</gravity>

    <scene>
      <ambient>0.7 0.7 0.7 1</ambient>
      <background>0.9 0.9 0.9 1</background>
    </scene>

    <light name="sun" type="directional">
      <pose>0 0 50 0 0 0</pose>
      <diffuse>1 1 1 1</diffuse>
      <specular>0.1 0.1 0.1 1</specular>
      <attenuation>
        <range>500</range>
        <constant>1.0</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>-0.5 0.5 -1</direction>
    </light>

    <gui>
      <camera name="default">
        <pose>0 0 80 0 0 0</pose>
      </camera>
    </gui>

    <include>
      <uri>model://roads_mesh</uri>
    </include>

    <model name="ground_plane">
      <static>true</static>
      <pose>0 0 0 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>2000 2000</size>
            </plane>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>2000 2000</size>
            </plane>
          </geometry>
          <material>
            <diffuse>0.2 0.2 0.2 1</diffuse>
            <ambient>0.1 0.1 0.1 1</ambient>
          </material>
        </visual>
      </link>
    </model>

  </world>
</sdf>
"""
    world_xml = world_xml.format(world_name=world_name)
    output_world_path.parent.mkdir(parents=True, exist_ok=True)
    with output_world_path.open("w") as f:
        f.write(world_xml)

    print(f"[OK] World SDF saved: {output_world_path}")


def sync_ackermann_world(world_out: Path, model_dir: Path):
    if not ACKERMANN_PROJECT_DIR.exists():
        print(f"[WARN] Ackermann project not found at {ACKERMANN_PROJECT_DIR}; skipping sync.")
        return

    target_path = ACKERMANN_WORLD_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(world_out, target_path)
    print(f"[INFO] Copied world to Ackermann project: {target_path}")

    target_models_root = ACKERMANN_PROJECT_DIR / "saye_description/worlds/models"
    target_model_dir = target_models_root / "roads_mesh"
    if target_model_dir.exists():
        shutil.rmtree(target_model_dir)
    shutil.copytree(model_dir, target_model_dir)
    print(f"[INFO] Copied road mesh model to Ackermann project: {target_model_dir}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build an OBJ/SDF road mesh starting from merged road polygons."
    )
    parser.add_argument(
        "input_json",
        help="Path to maps/road_polygons_merged.json",
    )
    parser.add_argument(
        "output_world",
        nargs="?",
        default="worlds/map.sdf",
        help="Destination world SDF (default: worlds/map.sdf)",
    )
    return parser.parse_args()


# ================================================================
# MAIN
# ================================================================

def main():
    args = parse_args()

    json_in = Path(args.input_json)
    world_out = Path(args.output_world)
    world_name = world_out.stem

    print(f"[INFO] Loading merged road polygons from: {json_in}")
    with json_in.open("r") as f:
        data = json.load(f)

    # Cada entrada tiene "merged_polygons": [ [ [x,y], ... ], ... ]
    polygons = []
    for entry in data.values():
        merged_polys = entry.get("merged_polygons", [])
        for coords in merged_polys:
            if len(coords) < 3:
                continue
            try:
                poly = Polygon(coords)
            except Exception as exc:
                print(f"[WARN] Invalid polygon skipped ({exc})")
                continue

            if poly.is_empty:
                continue

            if not poly.is_valid:
                poly = poly.buffer(0)
                if poly.is_empty:
                    continue

            polygons.append(poly)

    if not polygons:
        print("[ERROR] No polygons found after processing.")
        sys.exit(1)

    model_dir = Path("worlds/models/roads_mesh")
    mesh_rel = "meshes/roads_mesh.obj"
    mesh_out = model_dir / mesh_rel

    # Limpia modelo anterior si existe
    if model_dir.exists():
        shutil.rmtree(model_dir)

    build_obj_from_polygons(polygons, mesh_out)
    create_model_sdf(model_dir, mesh_rel)
    create_model_config(model_dir)
    create_world_sdf(world_out, world_name)
    sync_ackermann_world(world_out, model_dir)

    print("[DONE] SDF world is ready.")


if __name__ == "__main__":
    main()
