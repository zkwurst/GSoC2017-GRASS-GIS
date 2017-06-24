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

#%option
#% key: product
#% required: yes
#% options: NED, other
#% answer: NED
#% label: Select USGS Data Product
#% description: Choose which available USGS datasets to query
#% guisection: USGS Data Selection
#%end

#%option
#% key: resolution
#% required: yes
#% options: 1 arc-second, 1/3 arc-second, 1/9 arc-second
#% answer: 1/3 arc-second
#% label: Product Resolution
#% description: Available resolutions
#% guisection: USGS Data Selection
#%end

#%option
#% key: format
#% required: yes
#% options: IMG, other
#% answer: IMG
#% label: Product Format
#% description: Available data formats
#% guisection: USGS Data Selection
#%end

#%option G_OPT_R_OUTPUT
#% key: output_file
#% description: New Map Name
#% answer:composite_tile.img
#% gisprompt: new,bin,file
#% guisection: Download
#%end

#%option G_OPT_M_REGION
#% key: region
#% label: Data Selection Region
#% guisection: Download
#%end

#%option G_OPT_R_INTERP_TYPE
#% key: method
#% label: Composite Map Interpolation Method
#% answer: nearest
#% guisection: Download
#%end

#%flag
#% key: r
#% label: Remove source imagery after map creation?
#% description: Remove downloaded source tiles and composite raster
#% guisection: Download
#%end



import requests # pip install requests
import sys
import os
import zipfile
import grass.script as gscript
#import urllib
#from Tkinter import *
#from tkFileDialog import *
#import time


def main():
    gui_product = options['product']
    gui_resolution = options['resolution']
    gui_format = options['format']
    gui_output = options['output_file']
    gui_region = options['region']
    gui_method = options['method']
    gui_r_flag = flags['r']
    
    print gui_product
    print gui_resolution
    print gui_format
    print gui_output
    print gui_region
    print gui_method
    print gui_r_flag
    
#    NED
#    1/3 arc-second
#    IMG
#    composite_tile.img
#    nearest
#    False
    
    
    

    print "\n************************\nNED Data Download Module\n\
    ************************"
    
    
    # GUI dialogue to specify working DIR
    
    
    
#"""    
#    # Set working directory 
#    home_dir = os.path.expanduser('~')
#    root = Tk()
#    root.withdraw()
#    root.update()
#    work_DIR = askdirectory(initialdir=home_dir, title="Please specify local download directory:")
#    
#    try:
#        os.chdir(work_DIR)
#        print "\nDownload directory:\t" + work_DIR
#        # root.destroy()
#    except:
#        if OSError:
#            print OSError
#            sys.exit(1)
#        if os.path.exists(work_DIR):
#            os.chdir(work_DIR)
#            print "\nDownload directory:\t" + work_DIR
#            root.destroy()
#        else:
#            os.makedirs(work_DIR)
#            print "\nDownload directory:\t" + work_DIR
#            root.destroy()
#    
#    # Ask to select or set desired g.region
#    # current region is default
#"""

#"""
#New attempt at getting map projection and region coordinates translated
#into NAD83 for TNM API query. Not working currently.
#
#My goal is to get the region coordinates from a given location, translate
#them into NAD83, send the TNM API query, and use r.proj to reproject the
#tiles when they're downloaded. I can't get m.proj to work correctly.
#"""

    # Check coordinate projection
    gproj = gscript.parse_command('g.proj', flags='g')
    gproj_datum = gproj['datum']
    gproj_ellipse = gproj['ellps']
    print "\nComputational Region SRS:\nName:\t\t{0}\nEllipse:\t{1}".format(
                                               gproj_datum, gproj_ellipse)

#   #Does not return useable string. 
    current_proj4 = gscript.parse_command('g.proj', flags='-jf')
    
    usgs_ned_proj4 = "+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs"

#   if SRS_datum != 'nad83':
        
    usgs_ned_proj4 = "+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs"

#   #Does not return useable string. 
    #current_proj4 = gscript.parse_command('g.proj', flags='-jf')

# Different test methods of hardcoding variable input
    ###current_proj4 = str(gscript.parse_command('g.proj', flags='jf'))
    ###str_current_proj4 = current_proj4.replace(':', '=')

    str_current_proj4 = "+proj=lcc +lat_1=36.16666666666666 +lat_2=34.33333333333334 +lat_0=33.75 +lon_0=-79 +x_0=609601.22 +y_0=0 +ellps=GRS80 +units=m +no_defs"
    ###str_current_proj4 = "+proj=lcc +lat_1=36.16666666666666 +lat_2=34.33333333333334 +lat_0=33.75 +lon_0=-79 +x_0=609601.22 +y_0=0 +no_defs +a=6378137 +rf=298.257222101 +towgs84=0.000,0.000,0.000 +to_meter=1"

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
    min_bbox = [minx, miny]
    max_bbox = [maxx, maxy]
    #list_bbox = ",".join((str(coord) for coord in float_bbox))
    print "min_bbox = {0}".format(min_bbox)
    print "max_bbox = {0}".format(max_bbox)

#"""
#I guess there has to be a better way to do this?
#Both min and max outputs end up being the same. I tried a bunch of
#different methods to figure it out and couldn't.
#"""

    min_nad83_coords = gscript.parse_command('m.proj', coordinates=min_bbox, proj_in=str_current_proj4, proj_out=usgs_ned_proj4, separator=',', flags='d')
    max_nad83_coords = gscript.parse_command('m.proj', coordinates=max_bbox, proj_in=str_current_proj4, proj_out=usgs_ned_proj4, separator=',', flags='d')
    
    print "min_nad83_coords = {0}".format(min_nad83_coords)
    print "max_nad83_coords = {0}".format(max_nad83_coords)




# Old version of converting coordinate output into TNM API format
#"""      
#    # If proj not NAD83, temporarily convert to NAD83 to get correct g.region
#    # convert g.region bounding box coords only, then reproject the tiles?
#    
#    # Call "g.region -bg" to get computational region coords
#    gregion = gscript.parse_command('g.region', flags='bg')
#    gregion_dict = {}
#    for key, value in gregion.iteritems():
#        gregion_keys = ['ll_n', 'll_s', 'll_w', 'll_e']
#        if key in gregion_keys:
#            gregion_dict[str(key)] = float(value)
#    
#    if gregion_dict['ll_n'] > gregion_dict['ll_s']:
#        maxy = gregion_dict['ll_n']
#        miny = gregion_dict['ll_s']
#    else:
#        maxy = gregion_dict['ll_s']
#        miny = gregion_dict['ll_n']
#    if gregion_dict['ll_w'] > gregion_dict['ll_e']:
#        maxx = gregion_dict['ll_w']
#        minx = gregion_dict['ll_e']
#    else:
#        maxx = gregion_dict['ll_e']
#        minx = gregion_dict['ll_w']
#        
#    float_bbox = [minx, miny, maxx, maxy]
#    list_bbox = ",".join((str(coord) for coord in float_bbox))
#    print "\nComputational Region Coordinates\n{0}".format(float_bbox)
#"""    
    
    
    
    
#    
#    # Need to not hardcode these variables
#    datasets = urllib.quote_plus('National Elevation Dataset (NED) 1/3 arc-second')
#    bbox = urllib.quote_plus(list_bbox)
#    prodFormats = urllib.quote_plus('IMG')
#    
#    base_TNM = "https://viewer.nationalmap.gov/tnmaccess/api/products?"
#    datasets_TNM = "datasets={0}".format(datasets)
#    bbox_TNM = "&bbox={0}".format(bbox)
#    prodFormats_TNM = "&prodFormats={0}".format(prodFormats)
#    TNM_API_URL = base_TNM + datasets_TNM + bbox_TNM + prodFormats_TNM
#    
#    # Query TNM API for data availability
#    try:
#        TNM_API_GET = requests.get(TNM_API_URL, timeout=12)
#        returnJSON = TNM_API_GET.json()
#        # Parse JSON to return download URL
#        tile_APIcount = int(returnJSON['total'])
#        dwnld_size = []
#        dwnld_URL = []
#        dataset_name = []
#        if tile_APIcount > 0:
#            # Ask for user permission to proceed:
#                # Give estimated file size, time to complete
#            for tile in returnJSON['items']:
#                dwnld_size.append(int(tile['sizeInBytes']))
#                dwnld_URL.append(str(tile['downloadURL']))
#                if tile['datasets'][0] not in dataset_name:
#                    if len(dataset_name) <= 1:
#                        dataset_name.append(str(tile['datasets'][0]))
#                    else:
#                        print "Incompatible datasets detected."
#                        sys.exit(1)
#        else:
#            print "NED imagery is not available for the given parameters."
#            sys.exit(1)
#        print "\nDataset:\t{0}".format(dataset_name)
#        print "# of tiles:\t{0}".format(str(tile_APIcount))
#        total_size = sum(dwnld_size)
#        if 6 < len(str(total_size)) < 10:
#            print "Download Size:\t{0} MB".format(total_size * 1e-6)
#        if len(str(total_size)) >= 10:
#            print "Download Size:\t{0} GB".format(total_size * 1e-9)
#        # ask user permission before proceeding
#        proceed = raw_input("\nWould you like to download this data? (y/n):\t")
#        if proceed == "n":
#            print "\nDownload cancelled."
#            sys.exit(1)
#        if proceed == "y":
#            print "\nPlease wait.\nDownloading NED Data...\n"
#    except requests.exceptions.Timeout:
#        print "\nUSGS API query has timed out.\n"
#        sys.exit(1)
#    
#    LT_count = 0
#    LT_fullpaths = []
#    LT_basenames = []
#    
#    try:
#        for url in dwnld_URL:
#            dwnldREQ = requests.get(url, timeout=12, stream=True)
#            zipName = url.split('/')[-1]
#            local_temp = work_DIR + '/' + zipName
#            imgName = "img" + zipName.split('.')[0] + "_13.img"
#            LT_base = imgName.split('.')[0]
#            # Write ZIP archive to HD without writing entire request to memory
#            with open(local_temp, "wb+") as tempZIP:
#                for chunk in dwnldREQ.iter_content(chunk_size=1024):
#                    if chunk:
#                        tempZIP.write(chunk)
#            # Index into zip dir to retrieve and save IMG file
#            # Could potentially do this while ZIP in memory or too large?
#            with zipfile.ZipFile(local_temp, "r") as read_ZIP:
#                for f in read_ZIP.namelist():
#                    if str(f) == imgName:
#                        read_ZIP.extract(f, work_DIR) 
#            # Delete original ZIP archive
#            os.remove(local_temp)
#            LT_path = work_DIR + '/' + imgName
#            if os.path.exists(LT_path):
#                LT_count += 1
#                # not sure if r.patch can take full path or not
#                # inserted os.chdir above to test 
#                LT_fullpaths.append(imgName)
#                LT_basenames.append(LT_base)
#                print "Tile {0} of {1}: '{2}' downloaded to '{3}'".format(\
#                        LT_count, tile_APIcount, imgName, work_DIR)
#            else:
#                print "Download Unsuccesful."
#                sys.exit(1)
#    except requests.exceptions.Timeout:
#        print "\nUSGS download request has timed out.\n"
#        sys.exit(1)
#        
#    if LT_count == tile_APIcount:
#        print "\n{0} of {1} tiles succesfully downloaded.".format(LT_count,\
#               tile_APIcount)
#    
#    print "\n**************************\nNED Data Downloaded\n\
#    **************************\n"
#    
#    print "\nPatching NED Tiles to current g.region boundary."
#    
#    if LT_count == 1:
#        gscript.run_command('r.import', input = LT_fullpaths, \
#                            output = LT_basenames, overwrite=True)
#    if LT_count > 1:
#        for r in LT_fullpaths:
#            LT_file_name = r.split('/')[-1]
#            LT_layer_name = LT_file_name.split('.')[0]
#            # Defined earlier in script
#            # LT_basenames.append(LT_layer_name)
#            gscript.run_command('r.import', input = r,  \
#                                output = LT_layer_name, overwrite=True)
#        gscript.run_command('r.patch', input=LT_basenames, \
#                            output='test_combo_patch.img', overwrite=True)
#        print "\nImporting Patched Tile to GRASS GIS."
#    else:
#        print "Import Error. Number of input tiles is 0."
#        sys.exit(1)
#    
#    print "\n****************************\nr.in.usgsned Module Complete\n\
#    ****************************\n"

if __name__ == "__main__":
    options, flags = gscript.parser()
    main()
