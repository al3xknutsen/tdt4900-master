import omni.client
from pxr import Usd, UsdGeom, Gf

def open_stage(stage_url):
    return Usd.Stage.Open(stage_url)

def start_omniverse(do_live_edit):
    omni.client.usd_live_set_default_enabled(do_live_edit)

def save_stage(stage):
    stage.GetRootLayer().Save()
    omni.client.usd_live_process()

def create_cube(stage, mesh_url, coords):
    mesh = UsdGeom.Mesh.Define(stage, mesh_url)

    h = 0.5
    # All faces' vertex indices
    boxVertexIndices = [ 0,  1,  2,  1,  3,  2,
                        4,  5,  6,  4,  6,  7,
                        8,  9, 10,  8, 10, 11,
                        12, 13, 14, 12, 14, 15,
                        16, 17, 18, 16, 18, 19,
                        20, 21, 22, 20, 22, 23 ]
    # Number of vertices per face (one cube has 12 triangle faces)
    boxVertexCounts = [ 3 ] * 12
    # Vertex coordinates
    boxPoints = [ ( h, -h, -h), (-h, -h, -h), ( h,  h, -h), (-h,  h, -h),
                ( h,  h,  h), (-h,  h,  h), (-h, -h,  h), ( h, -h,  h),
                ( h, -h,  h), (-h, -h,  h), (-h, -h, -h), ( h, -h, -h),
                ( h,  h,  h), ( h, -h,  h), ( h, -h, -h), ( h,  h, -h),
                (-h,  h,  h), ( h,  h,  h), ( h,  h, -h), (-h,  h, -h),
                (-h, -h,  h), (-h,  h,  h), (-h,  h, -h), (-h, -h, -h) ]
    
    # Surface color
    mesh.CreateDisplayColorAttr([(0.463, 0.725, 0.0)])

    mesh.CreatePointsAttr(boxPoints)
    mesh.CreateFaceVertexCountsAttr(boxVertexCounts)
    mesh.CreateFaceVertexIndicesAttr(boxVertexIndices)

    # Translation
    translate = mesh.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
    translate.Set(Gf.Vec3d(coords[:3]))

    return mesh