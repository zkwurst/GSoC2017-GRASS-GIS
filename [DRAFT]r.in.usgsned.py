#%%file r.in.usgsned.py
#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
MODULE:     r.in.usgsned

AUTHOR:     Zechariah Krautwurst

MENTORS:    Anna Petrasova
            Vaclav Petras

PURPOSE:    Download user-requested tiles from USGS NED database.

COPYRIGHT:  (C) 2017 Zechariah Krautwurst and the GRASS Development Team
            
            This program is free software under the GNU General Public
            License (>=v2). Read the file COPYING that comes with GRASS
            for details.
            
VERSION:    [EARLY DRAFT] 
            
            Preliminary testing phase. Script imports NED IMG tiles from
            GRASS GIS locations by computational region boundary.
            Coordinates must be set to NAD83 for the script to work.
            Later versions will automatically convert SRS to NAD83,
            patch multiple tiles, and clip to computational region.
            
NOTES:      Needs:
            - Proper module formatting, function defs, pep8, etc
            - User input/control
            - GUI
            - Relative paths
            - GRASS formatting and interface
            - GRASS r.import, r.patch, g.proj conversion
            - Error handling
            - Comments/documentation
            - Code simplification
            - html, makefile, compilation
"""

#%module
#% description: Download USGS NED data
#% keyword: raster
#% keyword: NED
#%end

import requests # pip install requests
import sys
import os
import zipfile
import grass.script as gscript
import urllib
from Tkinter import *
from tkFileDialog import *
import time

print "\n************************\nNED Data Download Module\n\
************************"


# GUI dialogue to specify working DIR
"""
# Set working directory 
home_dir = os.path.expanduser('~')
root = Tk()
root.withdraw()
root.update()
work_DIR = askdirectory(initialdir=home_dir, title="Please specify local download directory:")
'''

work_DIR = "/home/zechariah/Downloads/test_NED_multi"

try:
    os.chdir(work_DIR)
    print "\nDownload directory:\t" + work_DIR
    
'''
    root.destroy()
except:
    if OSError:
        print OSError
        sys.exit(1)
    if os.path.exists(work_DIR):
        os.chdir(work_DIR)
        print "\nDownload directory:\t" + work_DIR
        root.destroy()
    else:
        os.makedirs(work_DIR)
        print "\nDownload directory:\t" + work_DIR
        root.destroy()
        
        

# Ask for desired g.region
# current region is default
# otherwise, provide g.region dialogue

# Check coordinate projection
gproj = gscript.parse_command('g.proj', flags='g')
SRS_name = gproj['name']
SRS_ellipse = gproj['ellps']
print "\nComputational Region SRS:\nName:\t\t{0}\nEllipse:\t{1}".format(
                                           SRS_name, SRS_ellipse)
if SRS_name != 'NAD83':
    print "\nGRASS GIS Location must be set to NAD83.\n\
    Conversion functionality will be implemented shortly."
    sys.exit(1)
    
# If proj not NAD83, temporarily convert to NAD83 to get correct g.region

# Call "g.region -bg" to get computational region coords
gregion = gscript.parse_command('g.region', flags='bg')
gregion_dict = {}
for key, value in gregion.iteritems():
    gregion_keys = ['ll_n', 'll_s', 'll_w', 'll_e']
    if key in gregion_keys:
        gregion_dict[str(key)] = float(value)

if gregion_dict['ll_n'] > gregion_dict['ll_s']:
    maxy = gregion_dict['ll_n']
    miny = gregion_dict['ll_s']
else:
    maxy = gregion_dict['ll_s']
    miny = gregion_dict['ll_n']
if gregion_dict['ll_w'] > gregion_dict['ll_e']:
    maxx = gregion_dict['ll_w']
    minx = gregion_dict['ll_e']
else:
    maxx = gregion_dict['ll_e']
    minx = gregion_dict['ll_w']
    
float_bbox = [minx, miny, maxx, maxy]
list_bbox = ",".join((str(coord) for coord in float_bbox))
print "\nComputational Region Coordinates\n{0}".format(float_bbox)

####
# Eventually used as GUI options

NEDdatasets = ['National Elevation Dataset (NED) 1 arc-second', \
               'National Elevation Dataset (NED) 1/3 arc-second', \
               'National Elevation Dataset (NED) 1/9 arc-second']

NEDformats = ['ArcGrid', 'FileGDB 10.1', 'GridFloat', 'IMG', 'Shapefile']

NEDproduct_extents = ['1 x 1 degree', '15 x 15 minute']
####

datasets = urllib.quote_plus('National Elevation Dataset (NED) 1/3 arc-second')
bbox = urllib.quote_plus(list_bbox)
prodFormats = urllib.quote_plus('IMG')

base_TNM = "https://viewer.nationalmap.gov/tnmaccess/api/products?"
datasets_TNM = "datasets={0}".format(datasets)
bbox_TNM = "&bbox={0}".format(bbox)
prodFormats_TNM = "&prodFormats={0}".format(prodFormats)
TNM_API_URL = base_TNM + datasets_TNM + bbox_TNM + prodFormats_TNM

# Query TNM API for data availability
try:
    TNM_API_GET = requests.get(TNM_API_URL, timeout=12)
    returnJSON = TNM_API_GET.json()
    # Parse JSON to return download URL
    tile_APIcount = int(returnJSON['total'])
    dwnld_size = []
    dwnld_URL = []
    dataset_name = []
    if tile_APIcount > 0:
        # Ask for user permission to proceed:
            # Give estimated file size, time to complete
        for tile in returnJSON['items']:
            dwnld_size.append(int(tile['sizeInBytes']))
            dwnld_URL.append(str(tile['downloadURL']))
            if tile['datasets'][0] not in dataset_name:
                if len(dataset_name) <= 1:
                    dataset_name.append(str(tile['datasets'][0]))
                else:
                    print "Incompatible datasets detected."
                    sys.exit(1)
    else:
        print "NED imagery is not available for the given parameters."
        sys.exit(1)
    print "\nDataset:\t{0}".format(dataset_name)
    print "# of tiles:\t{0}".format(str(tile_APIcount))
    total_size = sum(dwnld_size)
    if 6 < len(str(total_size)) < 10:
        print "Download Size:\t{0} MB".format(total_size * 1e-6)
    if len(str(total_size)) >= 10:
        print "Download Size:\t{0} GB".format(total_size * 1e-9)
    # ask user permission before proceeding
    proceed = raw_input("\nWould you like to download this data? (y/n):\t")
    if proceed == "n":
        print "\nDownload cancelled."
        sys.exit(1)
except requests.exceptions.Timeout:
    print "\nUSGS API query has timed out.\n"
    sys.exit(1)

LT_count = 0
LT_fullpaths = []
LT_basenames = []

try:
    for url in dwnld_URL:
        dwnldREQ = requests.get(url, timeout=12, stream=True)
        zipName = url.split('/')[-1]
        local_temp = work_DIR + '/' + zipName
        imgName = "img" + zipName.split('.')[0] + "_13.img"
        LT_base = imgName.split('.')[0]
        # Write ZIP archive to HD without writing entire request to memory
        with open(local_temp, "wb+") as tempZIP:
            for chunk in dwnldREQ.iter_content(chunk_size=1024):
                if chunk:
                    tempZIP.write(chunk)
        # Index into zip dir to retrieve and save IMG file
        # Could potentially do this while ZIP in memory or too large?
        with zipfile.ZipFile(local_temp, "r") as read_ZIP:
            for f in read_ZIP.namelist():
                if str(f) == imgName:
                    read_ZIP.extract(f, work_DIR) 
        # Delete original ZIP archive
        os.remove(local_temp)
        LT_path = work_DIR + '/' + imgName
        if os.path.exists(LT_path):
            LT_count += 1
            # not sure if r.patch can take full path or not
            # inserted os.chdir above to test 
            LT_fullpaths.append(imgName)
            LT_basenames.append(LT_base)
            print "\nTile {0} of {1}: '{2}' downloaded to '{3}'".format(\
                    LT_count, tile_APIcount, imgName, work_DIR)
        else:
            print "Download Unsuccesful."
            sys.exit(1)
except requests.exceptions.Timeout:
    print "\nUSGS download request has timed out.\n"
    sys.exit(1)
    
if LT_count == tile_APIcount:
    print "\n{0} of {1} tiles succesfully downloaded.".format(LT_count,\
           tile_APIcount)
    print "\n**************************\nNED Data Download Complete\n\
**************************\n"

"""
"""

#############################################################
# Variables for testing without having to download

LT_count = 4
# For single test
LT_fullpaths = "/home/zechariah/Downloads/test_NED_single/imgn36w079_13.img"

# For multi test
LT_fullpaths = [\
                      "/home/zechariah/Downloads/test_NED_multi/imgn36w079_13.img",\
                      "/home/zechariah/Downloads/test_NED_multi/imgn36w080_13.img",\
                      "/home/zechariah/Downloads/test_NED_multi/imgn37w079_13.img",\
                      "/home/zechariah/Downloads/test_NED_multi/imgn37w080_13.img"]

LT_basenames = ['imgn36w079_13', 'imgn36w080_13', 'imgn37w079_13.img', 'imgn37w080_13.img']

# Request user input name for output file
# combo_file_name = raw_input("Enter file name for GRASS region NED file:\t")
# combo_file_path = work_DIR + '/' + combo_file_name + ".img"

# For testing
combo_file_name = "test_combo_file"

##############################################################
"""


"""
# Option 1: Patch before import, import single patched clipped file

for r in LT_fullpaths:
    LT_file_name = r.split('/')[-1]
    LT_layer_name = LT_file_name.split('.')[0]
    if LT_count > 1:
        rpatch = gscript.run_command('r.patch', input=LT_fullpaths, \
                                 output='test_combo_patch', flags='overwrite')
        rimport_ned = gscript.run_command('r.import', input = 'test_combo_patch', \
                                          output = combo_file_name, flags = 'overwrite')
    else:
        rimport_ned = gscript.run_command('r.import', input = r, \
                                          output = LT_layer_name, flags = 'overwrite')
# Option 2: Import whole tiles and 
    
for r in LT_fullpaths:
    LT_file_name = r.split('/')[-1]
    LT_layer_name = LT_file_name.split('.')[0]
    rimport_ned = gscript.run_command('r.import', \
                                      input=r, \
                                      output=LT_layer_name, \
                                      flags='overwrite',\
                                      extent='region'\
                                      )
if LT_count > 1:
    rpatch = gscript.run_command('r.patch', input=LT_basenames, \
                                 output='test_combo_patch', flags='overwrite')
    
"""

gscript.run_command('r.import',\
                    input='/home/zechariah/Downloads/test_NED_multi/imgn36w079_13.img', \
                    output='imgn36w079_13')



'''
Input order may cause r.patch to fail but shouldn't because TNM API 
returns tiles in adjacent order.

Region may need to be temporarily changed to encompass all tiles to be patched,
then reset to original.

Not sure if input list needs full paths or already need to be imported,
or if list needs to be full path names.

temp_region = gscript.run_command('g.region', raster=LT_names)
'''


    
'''
if __name__ == "__main__":
    options, flags = grass.parser()
    main()
'''