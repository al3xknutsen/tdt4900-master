import numpy as np
from osgeo import gdal

def transform_vertices(path, vertices):
    # Open transform file
    with open(path) as file_transform:
        transform = file_transform.readlines()
    
    # Parse transformation matrix
    transform = list(map(lambda line: list(map(lambda coord: float(coord), line.strip().split())), transform))
    transform = np.array(transform).T

    # Transform vertices!
    vertices_transformed = ([((*v, 1.0) @ transform)[:2] for v in vertices])
    
    return vertices_transformed

def compute_bounding_box(all_coords):
    x, y = zip(*[c[1] for c in all_coords])
    bounding_box = (min(x), max(y), max(x), min(y))

    return bounding_box

def transform_range(old_value, old_min, old_max, new_min, new_max):
    new_value = (((old_value - old_min) * (new_max - new_min)) / (old_max - old_min)) + new_min
    return new_value

def read_obj(path_obj, path_transform):
    # Read OBJ file
    with open(path_obj) as objfile:
        obj = objfile.read()
    
    lines = obj.split("\n")
    
    # Store relevant data
    mtllines = []
    vertices = []
    uvs = []

    # Store the line number of the first UV coordinate pair
    uvs_start = None

    # Collect line numbers and contents of material, vertex, and uv lines
    for i, line in enumerate(lines):
        if line.startswith("usemtl "):
            mtllines.append((i, line))
        elif line.startswith("v "):
            vertices.append([float(c) for c in line.split()[1:]])
        elif line.startswith("vt "):
            uvs.append(float(c) for c in line.split()[1:])
            if not uvs_start:
                uvs_start = i

    # Add a final, end-of-file dummy line to the materials list
    mtllines.append((len(lines), ""))

    # Transform all vertex coordinates based on global.fwt
    vertices = transform_vertices(path_transform, vertices)

    return lines, mtllines, vertices, uvs, uvs_start

def crop_texture(name, img, bounding_box):
    path_cropped = f"/wavefrontobj/materials_textures/{name}.png"
    gdal.Translate(path_cropped, img, format="PNG", projWin=bounding_box)

def normalize_uvs(all_coords, bounding_box):
    minx, maxy, maxx, miny = bounding_box
    normalized = list(map(lambda c: (c[0], (round(transform_range(c[1][0], minx, maxx, 0, 1), 6),
                                            round(transform_range(c[1][1], miny, maxy, 0, 1), 6))),
                            all_coords))
    
    return normalized

def update_uvs(path_obj, path_result, path_transform, path_img):
    # Open image texture
    img = gdal.Open(path_img)

    lines, mtllines, vertices, uvs, uvs_start = read_obj(path_obj, path_transform)

    # Loop through all materials
    for i in range(len(mtllines) - 1):
        # Find the name of the current material, as well as its start and end lines
        name = mtllines[i][1].split()[1]
        index_start = mtllines[i][0]
        index_end = mtllines[i + 1][0]

        # Extract vertex, uv, and normal data from material lines
        lines_data = lines[index_start + 1:index_end]
        lines_data = list(filter(lambda line: line.startswith("f "), lines_data))

        # Store all UTM coordinates, to compute bounding box later
        all_coords = []

        # Loop through all faces having the current material
        for line in lines_data:

            # Find UV coordinates for each face, as well as its line number
            data_face = [f.split("/") for f in line.split()[1:]]
            data_uv = [(int(f[1]), uvs[int(f[1]) - 1]) for f in data_face if f[1]]

            # Skip if there is no UV data
            if not data_uv:
                continue
            
            # Extract all UTM vertex coordinates belonging to the current face
            data_vertex = [(int(f[1]), vertices[int(f[0]) - 1]) for f in data_face]
            all_coords.extend(data_vertex)
        
        # Skip if there are no vertex coordinates!
        if not all_coords:
            continue
        
        # Compute the bounding box (in UTM coordinates)
        bounding_box = compute_bounding_box(all_coords)

        # Crop the texture to the bounding box
        crop_texture(name, img, bounding_box)

        # Normalize vertex coordinates to range [0, 1],
        # in practice converting them to UV coordinates
        normalized = normalize_uvs(all_coords, bounding_box)
        
        # Update UV coordinates
        for i, c in normalized:
            uvs[i - 1] = c

    # Update UV coordinate lines
    uvs_str = [f"vt {u:.6f} {v:.6f}" for u, v in uvs]
    lines[uvs_start:uvs_start + len(uvs)] = uvs_str

    # Write result!
    result = "\n".join(lines)
    with open(path_result, "w") as objfile:
        objfile.write(result)

if __name__ == "__main__":
    # Define paths
    path_obj = "wavefrontobj/Bygninger.obj"
    path_result = "wavefrontobj/Bygninger.obj"
    path_transform = "wavefrontobj/global.fwt"
    path_img = "33-2-464-216-02.tif"

    update_uvs(path_obj, path_result, path_transform, path_img)
    
