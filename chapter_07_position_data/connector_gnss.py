import argparse
import csv
import time

from pxr import UsdGeom, Gf
from pyproj import CRS, Transformer
import numpy as np
import rasterio
from scipy.interpolate import interp2d

from omniverse_utils import start_omniverse, open_stage, save_stage

def project_to_utm(x, y, z):
    # Project from WGS84 (latlon) to UTM33N
    wgs84 = CRS.from_epsg(4326)
    utm33n = CRS.from_epsg(32633)
    transformer = Transformer.from_crs(wgs84, utm33n)
    new_x, new_z = transformer.transform(z, x)

    return (new_x, y, new_z)

def utm_offset(x, y, z):
    # Apply UTM offset
    new_x = x - 270630.659
    new_z = -(z - 7040355.576)
    new_y = y - 46.670

    return (new_x, new_y, new_z)

def translate(mesh, x, y, z):
    # Set new position of mesh
    mesh.GetOrderedXformOps()[0].Set(Gf.Vec3d(x, y, z))

def rotate(mesh, w, x, y, z):
    # Rotate mesh
    mesh.GetOrderedXformOps()[3].Set(Gf.Quatf(w, x, y, z))

def interpolate_raster(path_raster):
    # Read raster map
    raster = rasterio.open(path_raster)
    data = raster.read(1)

    # Generate an integer range for every pixel in the raster map
    x = np.arange(0, raster.width, 1.0)
    y = np.arange(0, raster.height, 1.0)
    
    # Interpolate values inbetween values in the integer ranges
    data_interpolated = interp2d(x, y, data, kind="cubic")

    # Transformation matrix to transform from UTM to pixel coords
    transform_inverse = np.linalg.inv(np.resize(raster.transform, (3, 3)))

    return transform_inverse, data_interpolated

def sample_raster(transform, data_interpolated, utm_x, utm_y):
    # Sample values from georeferenced raster based on pixel coords
    pixel_x, pixel_y = (transform @ (utm_x, utm_y, 1.0))[:-1]
    return data_interpolated(pixel_x, pixel_y)[0]

def extract_gnss(stage, filename, primname, rasterpath):
    # Obtains a variable reference to an already existing car object
    car = UsdGeom.Xform.Define(stage, f"/Root/{primname}")
    
    # Converts a list of strings to a list of floats
    def coords_to_float(row):
        return list(map(lambda c: float(c), row))
    
    # Store previous coordinates and quaternions
    coords_prev = []
    q_prev = []

    # Interpolated height map
    height_transform, height_interpolated = interpolate_raster(rasterpath)

    # Read CSV file with WGS84 coordinates
    with open(filename) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")

        for row in reader:
            # Cast coordinates from string to float
            coords = coords_to_float(row)

            # Project to UTM33N
            x, _, z = project_to_utm(coords[1], coords[2], coords[0])

            # Get height from interpolated height map
            y = sample_raster(height_transform, height_interpolated, x, z)

            # Apply UTM offset
            x, y, z = utm_offset(x, y, z)

            # Account for the fact that the GNSS sender, i.e. the center of
            # the car objects, is located on top of the car
            y += 1.5

            coords_current = np.asarray([x, y, z])

            # Only process rotation if the previous coordinate is different than the current,
            # and only if the current reading is not the first 
            if not np.array_equal(coords_current, coords_prev) and len(coords_prev) > 0:
                # Compute the rotation quaternion between the coordinate readings
                v1 = [0, 0, 1]
                v2 = coords_current - coords_prev
                xyz = np.cross(v1, v2)
                w = np.sqrt(np.linalg.norm(v1) ** 2 * np.linalg.norm(v2) ** 2) + np.dot(v1, v2)
                q = np.asarray([w, *xyz])
                q[1] = 0
                
                q /= np.linalg.norm(q)

                q_prev.append(q)

                # Perform smoothing by computing the average of the last 10 quaternions
                if len(q_prev) >= 10:
                    rotate(car, *np.average(np.asarray(q_prev), axis=0))
                    q_prev.pop(0)

            # Update variable for previous coordinate
            coords_prev = coords_current

            # Set position of mesh
            translate(car, x, y, z)

            # Save and wait
            save_stage(stage)
            time.sleep(0.01)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("primname")

    path_rasterpath = "7002_2_10m_z33.tif"

    start_omniverse(True)
    stage = open_stage("omniverse://gloshaugen.usd")

    args = parser.parse_args()
    extract_gnss(stage, args.path, args.primname)