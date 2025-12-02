#!/usr/bin/env python3
"""
build_sdf_roads_individual.py

Genera un mesh OBJ y un mundo SDF a partir de TODOS los polígonos de calles
de maps/road_polygons_merged.json, triangulando cada polígono de forma
individual (no se hace unary_union global).

Uso:
  python scripts/build_sdf_roads_individual.py maps/road_polygons_merged.json worlds/bari_world.sdf
"""

import json
import sys
import math
from pathlib import Path


# ================================================================
# TRIANGULACIÓN (fan + orientación CCW)
# ================================================================

def triangulate_polygon(poly):
    """
    Triangula un polígono usando fan triangulation desde el primer vértice.
    Fuerza orientación CCW (shoelace) para que las normales apunten hacia +Z.
    """
    if len(poly) < 3:
        return []

    # Shoelace para detectar orientación
    area = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += x1 * y2 - x2 * y1

    # Si el área es negativa → está CW → invertimos a CCW
    if area < 0:
        poly = list(reversed(poly))

    tris = []
    for i in range(1, len(poly) - 1):
        tris.append([poly[0], poly[i], poly[i + 1]])
    return tris


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
    """
    polygons: lista de polígonos, cada uno = [[x,y], [x,y], ...]
    """
    print("[INFO] Building roads OBJ mesh with one triangulation per street polygon...")

    vertices = []
    normals = []
    faces = []

    v_idx = 1
    n_idx = 1
    Z_ROAD = 0.05  # un poco por encima del ground_plane

    for poly in polygons:
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
          <diffuse>0.6 0.6 0.6 1</diffuse>
          <ambient>0.4 0.4 0.4 1</ambient>
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

def create_world_sdf(output_world_path: Path):
    world_xml = """<?xml version="1.6"?>
<sdf version="1.8">
  <world name="bari_world">

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
    output_world_path.parent.mkdir(parents=True, exist_ok=True)
    with output_world_path.open("w") as f:
        f.write(world_xml)

    print(f"[OK] World SDF saved: {output_world_path}")


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        print("Usage: python build_sdf_roads_individual.py <road_polygons_merged.json> [output_world.sdf]")
        sys.exit(1)

    json_in = Path(sys.argv[1])
    world_out = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("worlds/bari_world.sdf")

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
            polygons.append(coords)

    if not polygons:
        print("[ERROR] No polygons found in road_polygons_merged.json")
        sys.exit(1)

    model_dir = Path("worlds/models/roads_mesh")
    mesh_rel = "meshes/roads_mesh.obj"
    mesh_out = model_dir / mesh_rel

    # Limpia modelo anterior si existe
    if model_dir.exists():
        import shutil
        shutil.rmtree(model_dir)

    build_obj_from_polygons(polygons, mesh_out)
    create_model_sdf(model_dir, mesh_rel)
    create_model_config(model_dir)
    create_world_sdf(world_out)

    print("[DONE] SDF world is ready.")


if __name__ == "__main__":
    main()
