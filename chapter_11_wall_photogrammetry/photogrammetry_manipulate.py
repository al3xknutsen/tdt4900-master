from math import sqrt
import os

import numpy as np
import open3d
from shapely.geometry import Point, Polygon

from omniverse_utils import start_omniverse, open_stage, save_stage
from remove_verts import remove_vertices

def compute_face_normal(verts):
    # Use three vertices in computations
    p1, p2, p3 = verts[:3]

    # These two vectors are planar with each other
    v1 = p3 - p1
    v2 = p2 - p1

    # Computing the cross product gives a perpendicular vector, i.e. a normal
    cp = np.cross(v1, v2)
    cp /= np.linalg.norm(cp)

    return cp

def get_face_rotation(face):
    # Compute the XYZ components of the face's normal
    normal = compute_face_normal(face.T[:3,:3])
    a, b, c = normal
    
    # Utility
    absv = sqrt(a**2 + b**2 + c**2)
    l = sqrt(b**2 + c**2)

    if absv == 0:
        # Edge case: Normal is the zero vector (this is an error)
        matrix_rotate = np.identity(4)
    elif l == 0:
        # Edge case: Normal is parallel with the X axis
        matrix_rotate = np.asarray([[0, 0, 1, 0],
                                    [0, 1, 0, 0],
                                    [-1, 0, 0, 0],
                                    [0, 0, 0, 1]])
    else:
        # Compute rotation matrix from vector components alone
        matrix_rotate = np.asarray([[l / absv, -(a * b) / (l * absv), -(a * c) / (l * absv), 0],
                                    [0,        c / l,                 -b / l,                0],
                                    [a / absv, b / absv,              c / absv,              0],
                                    [0,        0,                     0,                     1]])

    return matrix_rotate

def homogenize(array):
    # Add homogeneous coordinates to matrix

    shape = array.shape
    # Create matrix with 1s
    points_homogeneous = np.ones((shape[0] + 1, shape[1]))
    # Paste matrix to 1s matrix
    points = np.asarray(array)
    points_homogeneous[:-1,:] = points

    return points_homogeneous

def generate_translation(translate):
    # Create a translation matrix from the given translation vector
    matrix = np.identity(4)
    matrix[:3,3] = translate
    return matrix

def get_face_bounding_box(face):
    # Generate a bounding box around a face extended along the z axis
    x, y, z, _ = zip(*face)
    bounding_box = (min(x), min(y), min(z) - 13, max(x), max(y), max(z) + 13)

    return bounding_box

def is_vert_within_bounding_box(vert, bounding_box):
    # Determine whether a vertex is within a bounding box
    x, y, z, _ = vert
    minx, miny, minz, maxx, maxy, maxz = bounding_box
    return minx < x < maxx and miny < y < maxy and minz < z < maxz

def filter_verts_within_face(face_transformed, photogram_transformed, points_photogram_mask, vertex_normals_photogram):
    # Procedure for filtering which vertices should be transformed.

    # Because the face has been aligned to the z axis, it can be treated as a 2D face
    # in the XY plane. Therefore, ignore the Z part of the vertex coordinates
    face_2d = face_transformed[:2,:].T

    # Compute a bounding box around the face
    bounding_box = get_face_bounding_box(face_transformed.T)

    # Enumerate all vertices of the photogrammetry mesh.
    # This is to keep track of which to remove after processing.
    photogram_enum = np.asarray(list(enumerate(photogram_transformed.T)), dtype="object")

    print("  Remove verts already moved")
    filter_ignore = photogram_enum[points_photogram_mask]
    filter_ignore_normals = vertex_normals_photogram[points_photogram_mask]
    vertices_and_normals = zip(filter_ignore, filter_ignore_normals)

    print("  Filter, bounding box")
    filter_bb = np.asarray(list(filter(lambda vert: is_vert_within_bounding_box(vert[0][1], bounding_box), vertices_and_normals)))

    print("  Filter, polygon")
    poly = Polygon(face_2d)
    filter_polygon = list(filter(lambda vert: poly.contains(Point(*vert[0][1][:2])), filter_bb))

    print("  Filter, vertex normals")
    # Check direction of vertex normals
    vertex_normals = np.asarray(filter_polygon)[:,1]
    dot_products = np.dot([0, 0, 1], vertex_normals.T)
    angled_correctly = np.less(dot_products, 0)
    # If more than half of the vertices point the right way, then
    # transform ALL vertices within that face
    most_angled_correctly = np.sum(angled_correctly) > angled_correctly.shape[0] / 2
    filter_angle = np.full_like(angled_correctly, most_angled_correctly)
    filter_vertex_normals = filter_ignore[filter_angle]

    # If no vertices will be transformed
    if len(filter_vertex_normals) == 0:
        return [], []

    # Return transformed vertices along with their indices
    indices, vertices = list(zip(*filter_vertex_normals))
    indices = list(indices)
    vertices = np.asarray(vertices).T

    return indices, vertices

def get_vertices_in_face(mesh):
    # Read attributes from Omniverse objects
    face_indices = mesh.GetAttribute("faceVertexIndices").Get()
    face_vertex_counts = mesh.GetAttribute("faceVertexCounts").Get()
    points = mesh.GetAttribute("points").Get()

    counter = 0
    faces = []

    # Group vertices per face
    for count in face_vertex_counts:
        indices = face_indices[counter:counter + count]
        faces.append([points[i] for i in indices])
        counter += count
    
    return faces

def transform_faces(points_photogram, vertex_normals_photogram, transform_building, transform_photogram, mesh_building):
    # Store groups of all photogrammetry vertices that have been processed
    flats = []

    # Get all faces in the building mesh
    faces = get_vertices_in_face(mesh_building)

    # Get a bool mask with all vertices in the photogrammetry mesh
    points_photogram_mask = np.asarray([True] * len(points_photogram))

    # Compute the inverse photogrammetry mesh transform
    transform_photogram_inv = np.linalg.inv(transform_photogram)

    # Homogenize photogrammetry mesh vertices
    points_photogram = homogenize(np.asarray(points_photogram).T)

    # Final scaling matrix to align photogrammetry vertices to the building mesh
    matrix_scale_z0 = np.asarray([[1, 0, 0, 0],
                                  [0, 1, 0, 0],
                                  [0, 0, 0, 0],
                                  [0, 0, 0, 1]])
    
    # Loop through all faces in the building mesh
    for i, face in enumerate(faces):
        print(i)
        print("Rotate face")
        
        transform_building = np.asarray(transform_building)

        # Homogenize current face
        face = homogenize(np.asarray(face).T[:3])

        # Convert face coordinates from object to world space
        face_global = transform_building @ face

        # Get the matrix to transform the building mesh so that the current face's normal
        # lies parallel to the Z axis. Also compute the inverse
        matrix = get_face_rotation(transform_building @ face)
        matrix_inv = np.linalg.inv(matrix)

        # Transform the building mesh
        face_transformed = matrix @ generate_translation(-face_global[:3,0]) @ transform_building @ face
        vertex_normals_transformed = (matrix[:3,:3] @ vertex_normals_photogram.T).T

        print("Rotate photogram mesh")
        photogram_transformed = matrix @ generate_translation(-face_global[:3,0]) @ transform_photogram @ points_photogram

        print("Filter vertices to flatten")
        photogram_indices, photogram_filter = filter_verts_within_face(face_transformed,
                                                                       photogram_transformed,
                                                                       points_photogram_mask,
                                                                       vertex_normals_transformed)

        # If no vertices within the current face are marked for processing:
        # Move to next face
        if len(photogram_indices) == 0:
            flats.append([])
            continue
            
        # Scale photogrammetry vertices by 0 along the Z axis!
        # This essentially moves them to the building mesh.
        print("Flatten photogram mesh")
        photogram_flat = matrix_scale_z0 @ photogram_filter
        # Transform everything back to their original transforms
        print("Unrotate photogram mesh")
        photogram_reverse = transform_photogram_inv @ generate_translation(face_global[:3,0]) @ matrix_inv @ photogram_flat

        flats.append(zip(photogram_indices, photogram_reverse.T))

        # Mask away all changed vertices
        points_photogram_mask[photogram_indices] = False

        print()
    
    return flats

def update_points(mesh, flats, path_obj):
    materials = []

    # Get content of material file
    path_mtl = os.path.splitext(path_obj)[0] + ".mtl"
    with open(path_mtl) as file_mtl:
        lines_materials = file_mtl.readlines()
    
    # Get material names
    for line in lines_materials:
        if line.startswith("newmtl "):
            materials.append(line.split()[1])
    
    vertices = np.asarray(mesh.vertices)

    # Get all indices to keep, i.e. all transformed vertices
    indices_keep = []
    for f in flats:
        for i, p in f:
            vertices[i] = p[:3]
            indices_keep.append(i)
    
    # Create a new OBJ file from the contents of the entire photogrammetry mesh
    open3d.io.write_triangle_mesh(path_obj, mesh, write_vertex_normals=False)

    # Read all lines from the newly created file
    with open(path_obj) as file_obj:
        lines = file_obj.readlines()
    
    # Update material names in the new file with the names
    # from the old file
    material_counter = 0
    for i, line in enumerate(lines):
        if line.startswith("usemtl "):
            lines[i] = f"usemtl {materials[material_counter]}\n"
            material_counter += 1
    
    # Overwrite OBJ and MTL files
    with open(path_obj, "w") as file_obj:
        file_obj.writelines(lines)
    
    with open(path_mtl, "w") as file_mtl:
        file_mtl.writelines(lines_materials)
    
    # Remove unprocessed vertices
    remove_vertices(path_obj, indices_keep)

if __name__ == "__main__":
    path_xform_building = "/Root/Elgesetergate_USD_Full_2/Bygninger/Shape_836/shape_1502"
    path_xform_photogram = "/Root/photogrammetry"
    path_mesh_photogram = f"{path_xform_photogram}/texturedMesh_obj/defaultobject/defaultobject"
    path_obj = "texturedMesh.obj"
    path_stage = "omniverse://gloshaugen.usd"
    path_mesh = "/Root/Elgesetergate_USD_Full_2/Bygninger/Shape_836/shape_1502/mesh"
    
    # Preliminary mesh manipulation
    scene = open3d.io.read_triangle_mesh(path_obj)
    scene.remove_duplicated_vertices()
    scene.compute_vertex_normals()
    vertex_normals_photogram = np.asarray(scene.vertex_normals)

    # Open Omniverse & stage
    start_omniverse(True)
    stage = open_stage(path_stage)
    
    # Get vertices and transforms of building and photogrammetry meshes
    points_photogram = np.asarray(scene.vertices)
    transform_world = stage.GetPrimAtPath(path_xform_building).GetAttribute("xformOp:transform").Get()
    transform_photogram = stage.GetPrimAtPath(path_xform_photogram).GetAttribute("xformOp:transform").Get()
    mesh_building = stage.GetPrimAtPath(path_mesh)
    flats = transform_faces(points_photogram, vertex_normals_photogram, transform_world.GetTranspose(), transform_photogram.GetTranspose(), mesh_building)

    # Remove unused points
    update_points(scene, flats, path_obj)
    save_stage(stage)
