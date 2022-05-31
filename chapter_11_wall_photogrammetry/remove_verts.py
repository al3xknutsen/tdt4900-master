import numpy as np

def remove_vertices(path_obj, indices_keep):
    print("Read from file")
    with open(path_obj) as file_obj:
        lines = file_obj.readlines()

    # Store vertices, faces, and materials
    verts = []
    faces = []
    mtls = []

    # Keep track of which line nummbers vertices and faces start with
    v_start = f_start = False
    v_start_index = f_start_index = 0

    # Keep length of vertices, uv indices, and faces attributes
    len_v = len_vt = 0

    # Get start line numbers of attributes
    print("Get initial positions")
    for i, line in enumerate(lines):
        if line.startswith("v "):
            if not v_start:
                v_start_index = i
                v_start = True
            verts.append(line)
            len_v += 1
        elif line.startswith("vt "):
            len_vt += 1
        elif line.startswith("f "):
            faces.append(line)
            if not f_start:
                f_start_index = i
                f_start = True
        elif line.startswith("usemtl "):
            mtls.append((i, line))
    
    verts = np.asarray(verts)
    faces = np.asarray(faces)
    
    # First material is dupe for some reason? Remove
    mtls.pop(0)

    print("Generate keep mask for vertices")
    verts_keep = np.asarray([False] * len(verts))
    verts_keep[indices_keep] = True
    print(verts_keep)

    print("Generate final list of vertices to keep")
    verts_final = verts[verts_keep]

    print("Find which faces to keep")
    print("  faces_vertex_indices")
    faces_vertex_indices = np.asarray([[int(c.split("/")[0]) for c in face.split()[1:]] for face in faces])

    # Generate keep mask for faces
    print("  faces_keep")
    faces_keep_mask = []
    for face in faces_vertex_indices:
        for vertex in face:
            if not verts_keep[vertex - 1]:
                faces_keep_mask.append(False)
                break
        else:
            faces_keep_mask.append(True)

    # Filter faces to keep
    faces_new = faces_vertex_indices[faces_keep_mask]
    faces_new_raw = faces[faces_keep_mask]

    print("Calculate new line numbers for materials")
    new_materials = []
    count_verts_final = len(verts_final)
    for e, (i, mtl) in enumerate(mtls):
        print(v_start_index + count_verts_final + len_vt + np.sum(faces_keep_mask[:i - f_start_index]) + e)
        new_materials.append((v_start_index + count_verts_final + len_vt + np.sum(faces_keep_mask[:i - f_start_index]) + e, mtl))

    print("Update vertex indices")
    faces_final = []
    for vertex_indices, face_raw in zip(faces_new, faces_new_raw):
        uvs = [int(f.split("/")[1]) for f in face_raw.split()[1:]]
        new_indices = [np.sum(verts_keep[:v]) for v in vertex_indices]
        face_final = " ".join(["f"] + ["/".join([str(x) for x in c]) for c in list(zip(new_indices, uvs))]) + "\n"
        faces_final.append(face_final)
    
    print("Replace content")
    lines[f_start_index:] = faces_final
    lines[v_start_index:v_start_index + len_v] = verts_final

    print("Add materials")
    for i, mtl in new_materials:
        lines.insert(i, mtl)

    print("Write to file")
    with open(path_obj, "w") as file_obj:
        file_obj.writelines(lines)
