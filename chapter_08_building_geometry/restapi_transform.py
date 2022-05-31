import numpy as np
from pxr import UsdGeom, Gf

from omniverse_utils import save_stage

def get_obj_file_list():
    # For now, only process one object at a time
    return ["uvmapping.obj"]

def add_to_scene(stage):
    print("Adding objects to scene...")
    obj_files = get_obj_file_list()

    for obj_file in obj_files:
        filename = obj_file.split(".")[0]
        UsdGeom.Xform.Define(stage, f"/Root/{filename}")
        root = stage.GetPrimAtPath(f"/Root/{filename}")
        root.GetReferences().AddReference(f"./assets/uvmapping/{obj_file}")
    save_stage(stage)

def import_transformation_matrix():
    print("Loading transformation matrix...")
    # Read transformation matrix from file
    with open(f"O:/assets/uvmapping/global.fwt") as file_transform:
        transform = file_transform.readlines()
    
    # Parse transformation matrix
    transform = list(map(lambda line: list(map(lambda coord: float(coord), line.strip().split())), transform))
    transform = np.array(transform).T

    # Apply offsets
    transform[3][0] -= 270630.659
    transform[3][1] = -(transform[3][1] - 7040355.576)
    transform[3][2] -= 46.670
    transform[3][1], transform[3][2] = transform[3][2], transform[3][1]

    return transform

def transform_mesh(stage, matrix_transform):
    print("Transforming objects...")
    matrix_usd = Gf.Matrix4d(matrix_transform)

    # Rotate mesh 90 degrees to account for difference in up axis
    matrix_rotation = Gf.Matrix4d()
    matrix_rotation.SetRotate(Gf.Rotation(Gf.Vec3d(1, 0, 0), -90))
    matrix_usd = matrix_rotation * matrix_usd

    obj_files = get_obj_file_list()

    # Add transformation matrix attribute
    for obj_file in obj_files:
        filename = obj_file.split(".")[0]
        prim = stage.GetPrimAtPath(f"/Root/{filename}")
        xform = UsdGeom.Xformable(prim)
        transform = xform.MakeMatrixXform()

        transform.Set(matrix_usd)

    save_stage(stage)
    print("Done!")
