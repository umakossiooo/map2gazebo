import json
import sys
import os
import math

# ================================================================
# TRIANGULATION (fan from first vertex)
# ================================================================

def triangulate_polygon(poly):
    """Triangulate a polygon using a simple fan from the first vertex."""
    if len(poly) < 3:
        return []
    triangles = []
    for i in range(1, len(poly) - 1):
        triangles.append([poly[0], poly[i], poly[i+1]])
    return triangles


# ================================================================
# NORMAL CALCULATION
# ================================================================

def compute_normal(p1, p2, p3):
    """Compute a unit normal for triangle (p1, p2, p3)."""
    ux, uy, uz = p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]
    vx, vy, vz = p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2]

    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx

    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length == 0:
        return 0.0, 0.0, 1.0

    return nx / length, ny / length, nz / length


# ================================================================
# BUILD OBJ MESH (supports MultiPolygon)
# ================================================================

def build_obj_from_polygons(polygons, output_obj_path):
    """
    Build a single OBJ mesh from all road polygons.

    polygons: list of entries, each entry is a list of polygons
              (because a road can be a MultiPolygon).
    """
    print("[INFO] Building OBJ asphalt mesh with normals...")

    vertices = []
    normals = []
    faces = []

    v_idx = 1
    n_idx = 1

    for group in polygons:         # each road's merged_polygons
        for poly in group:         # each poly is a list of [x, y]
            if len(poly) < 3:
                continue

            triangles = triangulate_polygon(poly)

            for tri in triangles:
                p1 = (tri[0][0], tri[0][1], 0.02)
                p2 = (tri[1][0], tri[1][1], 0.02)
                p3 = (tri[2][0], tri[2][1], 0.02)

                nx, ny, nz = compute_normal(p1, p2, p3)

                # vertices
                vertices.append(f"v {p1[0]} {p1[1]} {p1[2]}\n")
                vertices.append(f"v {p2[0]} {p2[1]} {p2[2]}\n")
                vertices.append(f"v {p3[0]} {p3[1]} {p3[2]}\n")

                # normals (one per vertex)
                normals.append(f"vn {nx} {ny} {nz}\n")
                normals.append(f"vn {nx} {ny} {nz}\n")
                normals.append(f"vn {nx} {ny} {nz}\n")

                # face line with vertex//normal indices
                faces.append(
                    f"f {v_idx}//{n_idx} {v_idx+1}//{n_idx+1} {v_idx+2}//{n_idx+2}\n"
                )

                v_idx += 3
                n_idx += 3

    os.makedirs(os.path.dirname(output_obj_path), exist_ok=True)
    with open(output_obj_path, "w") as obj:
        obj.writelines(vertices)
        obj.writelines(normals)
        obj.writelines(faces)

    print("[OK] OBJ mesh created at:", output_obj_path)
    print(f"     Vertices: {len(vertices)}")
    print(f"     Normals:  {len(normals)}")
    print(f"     Faces:    {len(faces)}")


# ================================================================
# CREATE model.sdf AND model.config
# ================================================================

def create_model_sdf(model_dir, mesh_rel):
    sdf_path = os.path.join(model_dir, "model.sdf")

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
          <diffuse>0.3 0.3 0.3 1</diffuse>
          <ambient>0.2 0.2 0.2 1</ambient>
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
    os.makedirs(model_dir, exist_ok=True)
    with open(sdf_path, "w") as f:
        f.write(sdf_xml)

    print("[OK] model.sdf created:", sdf_path)


def create_model_config(model_dir):
    cfg_path = os.path.join(model_dir, "model.config")

    cfg_xml = """<?xml version="1.0"?>
<model>
  <name>roads_mesh</name>
  <version>1.0</version>
  <sdf version="1.8">model.sdf</sdf>
  <author><name>map2gazebo</name></author>
  <description>Merged polygon-based asphalt mesh</description>
</model>
"""
    with open(cfg_path, "w") as f:
        f.write(cfg_xml)

    print("[OK] model.config created:", cfg_path)


# ================================================================
# WORLD FILE
# ================================================================

def create_world_sdf(output_world_path):
    world_xml = """<?xml version="1.6"?>
<sdf version="1.8">
  <world name="bari_world">

    <gravity>0 0 -9.81</gravity>

    <include>
      <uri>model://roads_mesh</uri>
    </include>

    <model name="ground_plane">
      <static>true</static>
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
        </visual>
      </link>
    </model>

  </world>
</sdf>
"""
    os.makedirs(os.path.dirname(output_world_path), exist_ok=True)
    with open(output_world_path, "w") as f:
        f.write(world_xml)

    print("[OK] World SDF saved:", output_world_path)


# ================================================================
# MAIN
# ================================================================

def main():
    if len(sys.argv) != 3:
        print("Usage: python build_sdf_roads.py <road_polygons_merged.json> <output_world.sdf>")
        sys.exit(1)

    json_in = sys.argv[1]
    world_out = sys.argv[2]

    print("[INFO] Loading merged polygons:", json_in)
    with open(json_in, "r") as f:
        raw = json.load(f)

    # Each entry has "merged_polygons": [ [ [x,y], ... ], ... ]
    polygons = [entry["merged_polygons"] for entry in raw.values()]

    model_dir = "worlds/models/roads_mesh"
    mesh_rel = "meshes/roads_mesh.obj"
    mesh_out = os.path.join(model_dir, mesh_rel)

    build_obj_from_polygons(polygons, mesh_out)
    create_model_sdf(model_dir, mesh_rel)
    create_model_config(model_dir)
    create_world_sdf(world_out)

    print("[DONE] SDF world is ready.")


if __name__ == "__main__":
    main()
