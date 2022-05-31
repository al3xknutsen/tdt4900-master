import imaplib
from getpass import getpass
import email
import os
import re
import shutil
import time
from urllib.request import urlretrieve 
import zipfile

from cryptography.fernet import Fernet, InvalidToken
import requests

def decrypt_passwords():
    # Checking for file existence
    if not os.path.exists("server.key") or \
       not os.path.exists("email.key") or \
       not os.path.exists("server.txt") or \
       not os.path.exists("email.txt"):
        print("Encryption files not found.\n")
        return None, None
    
    print("Loading encryption keys...")
    # Fetch keys
    with open("server.key", "rb") as server_keyfile:
        server_fernet = Fernet(server_keyfile.read())
    with open("email.key", "rb") as email_keyfile:
        email_fernet = Fernet(email_keyfile.read())
    
    try:
        print("Decrypting passwords...")
        # Decrypt passwords
        with open("server.txt", "rb") as server_passwordfile:
            server_password = server_fernet.decrypt(server_passwordfile.read()).decode()
        with open("email.txt", "rb") as email_passwordfile:
            email_password = email_fernet.decrypt(email_passwordfile.read()).decode()
    except InvalidToken:
        print("Password decryption failed!\n")
        return None, None

    print("Password decryption succeeded!\n")
    return server_password, email_password

def get_token(username, password):
    token_url = f"https://services.geodataonline.no/arcgis/tokens/generateToken"

    # Need password to log in to account
    password = password if password else getpass("Geodata Online password:")

    params = {
        "username": username,
        "password": password,
        "client": "requestip", # The token should be valid for the ip address that the request originated from
        "expiration": 1440, # 1440 minutes = 24 hours
        "f": "pjson" # The result should be JSON formatted
    }

    print("Requesting token...")
    response = requests.post(token_url, data=params).json()

    if "token" not in response:
        print("Token request unsuccessful! Terminating")
        return None

    token = response["token"]
    print(f"Token: {token}\n")

    return token

def submit_job(coords, projection, content, formats, epost, token):
    api_url = "https://services.geodataonline.no/arcgis/rest/services/Geoeksport/3DClipAndShip/GPServer/ClipAndShip3D/submitJob"

    # Valid content types
    possible_content = [
        "FKB (bygg, vann, veg)",
        "3D Bygg",
        "3D Bygg med taktekstur",
        "3D Bygg med taktekstur og veggtekstur",
        "Overflateobjekter (gjerder, stolper, etc.)",
        "Ortofoto",
        "Vegetasjon (laserdata)",
        "Tre/skog (generert fra laserdata)",
        "Detaljert terrengmodell"
    ]

    # Valid file formats
    possible_formats = [
        "ArcGIS Online",
        "ArcGIS Pro",
        "AutoCAD DWG",
        "IFC",
        "3D-PDF",
        "Collada",
        "Sketchup",
        "3ds",
        "CityGML",
        "LandXML",
        "Wavefront OBJ",
        "ArcGIS Enterprise"
    ]

    # Valid geographic projections
    possible_projections = [*[f"EPSG:2583{i} (UTM 3{i}N)" for i in range(2, 7)], "EPSG:3857 (Web Mercator)", "Lokal UTM-sone", "Lokal NTM-sone",
                            *[f"EPSG:51{str(i).zfill(2)} (NTM sone {i})" for i in range(5, 31)], "EPSG:4326 (WGS 1984)"]


    # Raise an error if projection, content, or file formats given are invalid
    if projection not in possible_projections:
        raise ValueError("Invalid projection")
    if not set(content).issubset(possible_content):
        raise ValueError("Invalid content")
    if not set(formats).issubset(possible_formats):
        raise ValueError("Invalid format")

    # Use default EPSG in area object
    epsg = projection.split()[0].split(":")[1] if projection.startswith("EPSG") else "25833"        

    # String defining the geometry of the area to be exported
    omrade = f'{{"geometryType":"esriGeometryPolygon","features":[{{"geometry":{{"rings":[{coords}],"spatialReference":{{"wkid":{epsg},"latestWkid":{epsg}}}}}}}],"sr":{{"wkid":{epsg},"latestWkid":{epsg}}}}}'

    # The name of the job
    navn = "script_test_2"

    # All data to be sent to the server
    data = {
        "omrade": omrade,
        "innhold": str(content),
        "format": str(formats),
        "navn": navn,
        "projeksjon": projection,
        "epost": epost,
        "Web_projeksjon": "Samme som leveranseprojeksjon",
        "min_vegetasjon_hoyde": 2,
        "f": "pjson",
        "env:outSR": epsg,
        "token": token
    }

    print("Submitting job to Geodata servers...")
    response = requests.post(api_url, data=data).json()

    if "jobId" not in response:
        print("Job submission unsuccessful! Terminating")
        return None
    
    jobid = response["jobId"]
    print(f"Job successfully submitted. Job ID: {jobid}\n")

    return jobid

def check_job_status(jobid, token):
    api_url = f"https://services.geodataonline.no/arcgis/rest/services/Geoeksport/3DClipAndShip/GPServer/ClipAndShip3D/jobs/{jobid}"

    params = {
        "f": "pjson", # Result should be JSON formatted
        "token": token # We need a valid token to access this API endpoint
    }

    status = ""
    statii = ["esriJobSucceeded", "esriJobFailed"]
    first = True

    print("Checking job status...")

    while status not in statii:
        if not first:
            time.sleep(600)
        first = False

        response = requests.get(api_url, params=params).json()
        if "jobStatus" in response:
            status = response["jobStatus"]
            print(f"Job status: {status}")

    if status == "esriJobSucceeded":
        print("Job has finished!\n")
        return True
    else:
        print("Job has failed!")
        return False

def get_download_url(epost, password):
    # We assume we're using a gmail account
    imap = imaplib.IMAP4_SSL("imap.gmail.com")

    password = password if password else getpass("Email account password: ")
    print("Logging into email account...")
    imap.login(epost, password)
    print("Logged in.")

    messages = imap.select("INBOX")[1]
    message_count = messages[0]

    def wait():
        # Mini function for waiting for email
        print("Email not yet received. Waiting...")
        time.sleep(60)

    while True:
        # Only look at the latest email in the inbox
        print("Fetching latest email...")
        msg_raw = imap.fetch(message_count, "(RFC822)")
        msg = email.message_from_bytes(msg_raw[1][0][1])

        # Ignore all mails not from the appropriate sender
        if msg["From"] != "Geodataonline@geodata.no":
            wait()
            continue

        # If the mail has the appropriate origin:
        # Try to find the download URL
        text = msg.get_payload(decode=True).decode()
        url = re.search(r"(?P<url>https://geodata-gdonline-gdo-processing-geoprocessing\.s3\.amazonaws\.com/gpresults/3DClipAndShip/.*)", text).group("url")

        # If no download URL was found, this probably means that the latest email
        # was the job start confirmation. Wait a bit more.
        if not url:
            wait()
            continue
        
        print("Email received!")
        return url

def download_files(url):
    # TODO: Remove already existing files on Nucleus
    print("Downloading files...")
    urlretrieve(url, "buildings.zip")
    print("Files downloaded!")

    print("Unzipping...")
    with zipfile.ZipFile("buildings.zip", "r") as zip:
        zip.extractall("buildings")
    print("Files unzipped!\n")

    # We don't need the zip file afterwards. Delete
    os.remove("buildings.zip")
    return

def embed_materials():
    # This is a function to embed material info in each obj file.
    # This is due to a bug in Omniverse/USD where adding a reference
    # to obj files will only add the obj files (not mtl files) in cache.
    # This will result in the mesh not rendering at all.

    # Getting a list of all .obj files
    files = os.listdir("buildings/wavefrontobj")
    obj_files = filter(lambda f: f.endswith(".obj"), files)

    for obj_file in obj_files:
        # Read the content of the .obj file
        obj_path = f"buildings/wavefrontobj/{obj_file}"
        with open(obj_path) as f:
            content = f.readlines()
        
        # Find the name of the .mtl file
        for line in content:
            if line.startswith("mtllib "):
                mtllib = line.split()[1]
                break
        
        # Read the materials file
        with open(f"buildings/wavefrontobj/{mtllib}") as mtlfile:
            materials = mtlfile.read()
        
        # Split the contents of the material file to a list of materials
        materials = "\n".join(materials.split("\n")[1:])
        materials = materials.split("\n\n")

        # Get a list of all materials referenced in the .obj file
        materials_in_file = [line.split()[1] for line in content if line.startswith("usemtl ")]

        embedded_materials = []

        # Get the material info from the .mtl file for all materials referenced in the .obj file
        for m_in_f in materials_in_file:
            for m in materials:
                if m.startswith(f"newmtl {m_in_f}"):
                    embedded_materials.append(m)
                    break
        
        # Transform material list to string
        embedded_materials = "\n\n".join(embedded_materials)
        
        # Remove the reference to the .mtl file and embed the material definitions themselves
        content_new = "".join(content).replace(f"mtllib {mtllib}", embedded_materials)
        
        # Write the updates to file
        with open(obj_path, "w") as f:
            f.write(content_new)

def cache_files(path_to_cache):
    print("Adding files to local cache...")
    shutil.copytree("buildings", path_to_cache)
    print("Files cached!")

def upload_to_nucleus(path):
    print("Uploading files to Omniverse Nucleus...")
    shutil.move(os.path.abspath("buildings"), path)
    print("Files uploaded!")
