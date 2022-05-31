from pxr import Usd
from omniverse_utils import open_stage, start_omniverse, save_stage
from pyproj import CRS, Transformer

def transform_meshes(stage):
    # Create transformer to convert from RoadRunner to UTM33N coordinatess
    proj_string = "+proj=tmerc +lat_0=63.41771242884644 +lon_0=10.40335350836009 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +vunits=m +no_defs"
    roadrunner = CRS.from_proj4(proj_string)
    utm33n = CRS.from_epsg(32633)
    transformer = Transformer.from_crs(roadrunner, utm33n)

    # Get roads object (should already be imported to Omniverse)
    roads = stage.GetPrimAtPath("/RoadRunner_export")

    # Loop through all road prims
    for prim in Usd.PrimRange(roads):
        # Only process meshes
        if prim.GetTypeName() != "Mesh":
            continue
        
        # Get vertex list
        points = prim.GetAttribute("points").Get()

        points_transformed = []
        
        # Transform points from RoadRunner to UTM33N, to Omniverse using offsets
        for p in points:
            x, z, y = p
            new_x, new_z = transformer.transform(x, z)
            new_x -= 270630.659
            new_z -= 7040355.576
            points_transformed.append((new_x, new_z, y))

        # Overwrite vertices
        prim.GetAttribute("points").Set(points_transformed)

        save_stage(stage)

if __name__ == "__main__":
    start_omniverse(True)
    stage = open_stage("omniverse://gloshaugen.usd")
    transform_meshes(stage)
