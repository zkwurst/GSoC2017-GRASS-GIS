# -*- coding: utf-8 -*-

import requests # pip install requests
import sys
import os
import zipfile


# Call "g.region -bg" to get computational region coords

# Write g.region output to URL bbox input function

singleURL = """http://viewer.nationalmap.gov/tnmaccess/api/products?
datasets=National Elevation Dataset (NED) 1/3 arc-second&
bbox=-78.74626600,35.67208711,-78.53147569,35.88217399&prodFormats=IMG"""

multiURL = """http://viewer.nationalmap.gov/tnmaccess/api/products?
datasets=National Elevation Dataset (NED) 1/3 arc-second&
bbox=-79.12944451,35.29814813,-78.13398155,36.27185184&prodFormats=IMG"""

"""
Something strange going on with http request. Seems like USGS server is
shutting the request down without returning the appropriate error message.
"""

# Query TNM API for data availability
try:
    singleREQ = requests.get(singleURL, timeout=12)
    returnJSON = singleREQ.json()
    # Parse JSON to return download URL
    # This will be modified to count and return number of tiles
    dwnldURL = returnJSON['items'][0]['downloadURL']
except requests.exceptions.Timeout:
    print "\nUSGS API query has timed out.\n"
    sys.exit(1)

try:
    # Send GET request to download URL
    single_dwnldREQ = requests.get(dwnldURL, timeout=12, stream=True)
except requests.exceptions.Timeout:
    print "\nUSGS download request has timed out.\n"
    sys.exit(1)

# Assign perm or temp download dir
# Working dir may change running through GRASS
# How to make OS independent parameter?
zipName = dwnldURL.split('/')[-1]
local_temp = "/home/Downloads/" + zipName

# Write ZIP archive to HD without writing entire request to memory
with open(local_temp, "wb+") as tempZIP:
    for chunk in single_dwnldREQ.iter_content(chunk_size=1024):
        if chunk:
            tempZIP.write(chunk)

# Index into zip dir to retrieve and save IMG file
# Could potentially do this while ZIP in memory or too large?
with zipfile.ZipFile(local_temp) as read_ZIP:
    for f in read_ZIP.namelist():
        imgName = zipName.split('.')[0] + ".img"
        if f is imgName:
            imgOut = "/home/Downloads/" + imgName
            read_ZIP.extract(f, imgOut)
            
# Delete original ZIP archive
os.remove(local_temp)

# Call r.import on imgOut

# If multiple tiles, call r.patch

