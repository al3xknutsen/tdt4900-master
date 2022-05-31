from omniverse_utils import open_stage, save_stage, start_omniverse
from pxr import UsdGeom, Sdf, UsdShade

def apply_texture(stage, mesh, uvs):
    # Add UV coordinates to mesh
    tex_coords = UsdGeom.Mesh(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    tex_coords.Set(uvs)
    tex_coords.SetInterpolation("vertex")

    # Create a new material (or get a reference to an already existing one)
    newMat = UsdShade.Material.Define(stage, "/Root/Bygninger/Looks/noname16")

    matPath = '/Root/Bygninger/Looks/noname16'

    # Create a diffuse shader and a texture coordinate reader
    diffuseColorShader = UsdShade.Shader.Define(stage, matPath+'/diffuseTex')
    primStShader = UsdShade.Shader.Define(stage, matPath+'/diffuseTex/TexCoordReader')
    primStShader.CreateIdAttr("UsdPrimvarReader_float2")
    primStShader.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    primStShader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")

    # Add attributes to the diffuse shader
    diffuseColorShader.CreateIdAttr("UsdUVTexture")
    texInput = diffuseColorShader.CreateInput("file", Sdf.ValueTypeNames.Asset)
    texInput.Set("./assets/textures/walls/manual_texture_1_corrected.jpg")
    texInput.GetAttr().SetColorSpace("RGB")
    diffuseColorShader.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(primStShader.CreateOutput("result", Sdf.ValueTypeNames.Float2))
    diffuseColorShaderOutput = diffuseColorShader.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    # Add a preview shader
    usdPreviewSurfaceShader = UsdShade.Shader.Define(stage, matPath+'/noname16')
    usdPreviewSurfaceShader.CreateIdAttr("UsdPreviewSurface")
    diffuseColorInput = usdPreviewSurfaceShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
    diffuseColorInput.ConnectToSource(diffuseColorShaderOutput)

    # Bind the material to the mesh
    UsdShade.MaterialBindingAPI(mesh).Bind(newMat)

if __name__ == "__main__":
    # Open omniverse
    start_omniverse(True)
    stage_path = "omniverse://gloshaugen.usd"
    stage = open_stage(stage_path)

    # Get a reference to the relevant mesh
    mesh = stage.GetPrimAtPath("/Root/Bygninger/Bygninger_obj/defaultobject/noname16")

    # Create a list with UV-coordinates (0,0)
    vertices = mesh.GetAttribute("points").Get()
    vertex_count = len(vertices)
    uvs = [(0, 0)] * vertex_count

    # Assign UV coordinates to the appropriate vertices
    uvs[1] = (1, 0)
    uvs[5] = (0, 1)
    uvs[6] = (0, 0)
    uvs[7] = (0, 1)
    uvs[8] = (0, 0)
    uvs[9] = (1, 1)

    apply_texture(stage, mesh, uvs)

    save_stage(stage)
