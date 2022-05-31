from pxr import UsdGeom, Gf
from omniverse_utils import open_stage, save_stage, start_omniverse, create_cube

def create_objs_at_verts(stage, mesh):
    # Define a new xprim to store the reference cubes
    url_refs = "/Root/refs"
    UsdGeom.Xform.Define(stage, url_refs)

    # Get the transform of the buildings prim
    xform_buildings = stage.GetPrimAtPath("/Root/Bygninger")
    transform = xform_buildings.GetAttribute("xformOp:transform").Get()

    # Apply the building transform to the vertex coordinates,
    # and add cubes at the transformed coordinates
    vertices = mesh.GetAttribute("points").Get()
    for i, v in enumerate(vertices):
        coords_world = Gf.Vec4d(*v, 1.0) * transform
        create_cube(stage, f"{url_refs}/v{i}", coords_world)

if __name__ == "__main__":
    # Open the USD scene
    start_omniverse(True)
    stage_path = "omniverse://gloshaugen.usd"
    stage = open_stage(stage_path)

    # Create reference cubes
    mesh = stage.GetPrimAtPath("/Root/Bygninger/Bygninger_obj/defaultobject/noname16")
    create_objs_at_verts(stage, mesh)
    save_stage(stage)
