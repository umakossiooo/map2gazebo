import json
import sys
import os
import math

# ----------------------------------
# Triangulation helper (earcut)
# ----------------------------------

def triangulate_polygon(polygon):
    """Simple earcut triangulation for convex or mostly convex polygons."""
    # NOTE: For your road polygons (long thin convex shapes), earcut is perfect.
    # This small triangulator avoids external heavy libs.
    if len(polygon) < 3:
        return []

    triangles = []
    for i in range(1, len(polygon) - 1):
        triangles.append([polygon[0], polygon[i], polygon[i+1]])
    return triangles


# ----------------------------------
# Main mesh builder
# ----------------------------------

def build_merged_obj(polygons, output_obj_path):
    vertices = []
    faces = []
    vcount = 1  # OBJ indices start at 1

    for poly in polygons:
        if len(poly) < 3:
            continue

        tris = triangulate_polygon(poly)

        for tri in tris:
            # Add triangle vertices
            tri_indices = []
            for (x, y) in tri:
                vertices.append(f"v {x} {y} 0.02\n")   # small height so it is visible
                tri_indices.append(vcount)
                vcount += 1

            # Create face
            faces.append(f"f {tri_indices[0]} {tri_indices[1]} {tri_indices[2]}\n")

    # Write OBJ
    os.makedirs(os.path.dirname(output_obj_path), exist_ok=True)
    with open(output_obj_path, "w") as f:
        f.writelines(vertices)
        f.writelines(faces)

    print(f"[OK] OBJ mesh created: {output_obj_path}")
    print(f"    Total vertices: {len(vertices)}")
    print(f"    Total faces: {len(faces)}")


def create_model_sdf(model_dir, mesh_rel_path):
    """Create model.sdf for the combined asphalt mesh."""
    sdf_path = os.path.join(model_dir, "model.sdf")
    os.makedirs(model_dir, exist_ok=True)

    sdf = f"""<?xml version="1.6" ?>
<sdf version="1.8">
  <model name="roads_mesh">
    <static>true</static>
    <link name="road_link">
      <visual name="road_visual">
        <geometry>
          <mesh>
            <uri>model://roads_mesh/{mesh_rel_path}</uri>
          </mesh>
        </geometry>
        <material>
          <ambient>0.2 0.2 0.2 1</ambient>
          <diffuse>0.3 0.3 0.3 1</diffuse>
        </material>
      </visual>
      <collision name="road_collision">
        <geometry>
          <mesh>
            <uri>model://roads_mesh/{mesh_rel_path}</uri>
          </mesh>
        </geometry>
      </collision>
    </link>
  </model>
</sdf>
"""
    with open(sdf_path, "w") as f:
        f.write(sdf)

    print(f"[OK] Model SDF created: {sdf_path}")


def create_world_sdf(output_world_path):
    """Create the main bari_world.sdf that includes the asphalt mesh."""
    world_sdf = f"""<?xml version="1.6" ?>
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
          <geometry><plane><normal>0 0 1</normal><size>2000 2000</size></plane></geometry>
        </collision>
        <visual name="visual">
          <geometry><plane><normal>0 0 1</normal><size>2000 2000</size></plane></geometry>
        </visual>
      </link>
    </model>

  </world>
</sdf>
"""
    os.makedirs(os.path.dirname(output_world_path), exist_ok=True)
    with open(output_world_path, "w") as f:
        f.write(world_sdf)

    print(f"[OK] World SDF created: {output_world_path}")


# ----------------------------------
# MAIN
# ----------------------------------

def main():
    if len(sys.argv) != 3:
        print("Usage: python build_sdf_roads.py <road_polygons.json> <output_world.sdf>")
        sys.exit(1)

    polygons_file = sys.argv[1]
    output_world = sys.argv[2]

    print("[INFO] Loading polygons:", polygons_file)
    with open(polygons_file, "r") as f:
        poly_data = json.load(f)

    # Extract polygons
    polygons = []
    for wid, entry in poly_data.items():
        polygons.append(entry["polygon"])

    # Build merged mesh
    model_dir = "worlds/models/roads_mesh"
    mesh_path = "meshes/roads_mesh.obj"
    mesh_full_path = os.path.join(model_dir, mesh_path)

    build_merged_obj(polygons, mesh_full_path)
    create_model_sdf(model_dir, mesh_path)
    create_world_sdf(output_world)

    print("[DONE] SDF world ready.")


if __name__ == "__main__":
    main()
