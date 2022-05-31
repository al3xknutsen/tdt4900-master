from restapi_buildings import check_job_status, get_download_url, get_token, submit_job, upload_to_nucleus, download_files, decrypt_passwords, embed_materials, cache_files
from restapi_transform import add_to_scene, import_transformation_matrix, transform_mesh
from omniverse_utils import start_omniverse, open_stage

def main():
    epost = "emailaddr@emailprovider.extension"
    username = "username"

    coords = [
        [270635.22491466044, 7040341.124050389],
        [270682.85000991065, 7040212.800877076],
        [270612.73528634786, 7040183.035192545],
        [270559.1570541914, 7040316.650043108],
        [270635.22491466044, 7040341.124050389]
    ]

    server_password, email_password = decrypt_passwords()

    token = get_token(username, server_password)
    if not token:
        return

    jobid = submit_job(coords, "EPSG:25833 (UTM 33N)", ["3D Bygg med taktekstur"], ["Wavefront OBJ"], epost, token)
    if not jobid:
        return
    
    if not check_job_status(jobid, token):
        return
    
    url = get_download_url(epost, email_password)
    download_files(url)
    cache_files("AppData/Local/ov/cache/client/omniverse/localhost/Users/test/assets")
    upload_to_nucleus("O:/assets")

    start_omniverse(True)
    stage_url = "gloshaugen.usd"
    stage = open_stage(stage_url)
    add_to_scene(stage)

    matrix = import_transformation_matrix()
    transform_mesh(stage, matrix)

if __name__ == "__main__":
    main()