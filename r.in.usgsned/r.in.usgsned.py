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
#% options: National Elevation Dataset (NED), other
#% answer: National Elevation Dataset (NED)
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

#%option G_OPT_M_MAPSET
#% key: mapset
#% description: USGS Mapset
#% answer: USGS Mapset
#% guisection: Download
#%end

#%option G_OPT_R_OUTPUT
#% key: output_file
#% description: New Composite Tile Map Name
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
import urllib
#from Tkinter import *
#from tkFileDialog import *
#import time


def main():
    gui_product = options['product']
    gui_resolution = options['resolution']
    gui_format = options['format']
    gui_mapset = options['mapset']
    gui_output = options['output_file']
    gui_region = options['region']
    gui_method = options['method']
    gui_r_flag = flags['r']

    print "\n************************\nNED Data Download Module\n************************"
    
    # GUI dialogue to specify working DIR?

    # Check coordinate projection
    gproj = gscript.parse_command('g.proj', flags='g')
    gproj_datum = gproj['datum']
    gproj_ellipse = gproj['ellps']
    print "\nComputational Region SRS:\nName:\t\t{0}\nEllipse:\t{1}".format(
                                               gproj_datum, gproj_ellipse)
    
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
    
    if gproj_datum == 'wgs84':
        str_bbox = ",".join((str(coord) for coord in float_bbox))
    else:
        #str_current_proj4 = gscript.read_command('g.proj', flags='jf')
        #print "Origin PROJ.4 string:\n{0}".format(str_current_proj4)
        # EPSG:4269
        usgs_ned_proj4 = "+proj=longlat +ellps=GRS80 +datum=NAD83 +nodefs"
        wgs84_proj4 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
        #print "USGS PROJ.4 string:\n{0}".format(usgs_ned_proj4)
        
        min_bbox = [minx, miny]
        max_bbox = [maxx, maxy]

        min_nad83_coords = gscript.read_command('m.proj', coordinates=min_bbox,\
                                                proj_in=wgs84_proj4, \
                                                proj_out=usgs_ned_proj4, \
                                                separator='comma', flags='d')
        max_nad83_coords = gscript.read_command('m.proj', coordinates=max_bbox,\
                                                proj_in=wgs84_proj4, \
                                                proj_out=usgs_ned_proj4, \
                                                separator='comma', flags='d')
        
        min_list = min_nad83_coords.split(',')[:2]
        max_list = max_nad83_coords.split(',')[:2]
        list_bbox = min_list + max_list
        str_bbox = ",".join((str(coord) for coord in list_bbox))

    gui_prod_str = gui_product + " " + gui_resolution
    datasets = urllib.quote_plus(gui_prod_str)
    #bbox = urllib.quote_plus(str_bbox)
    prodFormats = urllib.quote_plus(gui_format)
    
    base_TNM = "https://viewer.nationalmap.gov/tnmaccess/api/products?"
    datasets_TNM = "datasets={0}".format(datasets)
    bbox_TNM = "&bbox={0}".format(str_bbox)
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
        if tile_APIcount == 0:
            print "Zero tiles returned. Please check input parameters."
            sys.exit(1)
        print "\nDataset:\t{0}".format(dataset_name)
        print "# of tiles:\t{0}".format(str(tile_APIcount))
        total_size = sum(dwnld_size)
        if 6 < len(str(total_size)) < 10:
            print "Download Size:\t{0} MB".format(total_size * 1e-6)
        if len(str(total_size)) >= 10:
            print "Download Size:\t{0} GB".format(total_size * 1e-9)
        # ask user permission before proceeding
#        proceed = raw_input("\nWould you like to download this data? (y/n):\t")
#        if proceed == "n":
#            print "\nDownload cancelled."
#            sys.exit(1)
#        if proceed == "y":
#            print "\nPlease wait.\nDownloading NED Data...\n"
    except requests.exceptions.Timeout:
        print "\nUSGS API query has timed out.\n"
        sys.exit(1)
#"""    
#    current_gisdbase = gscript.read_command('g.gisenv', get='GISDBASE')
#    current_location = gscript.read_command('g.gisenv', get='LOCATION_NAME')
#    
#    gscript.run_command('g.mapset', mapset=gui_mapset, \
#                        location=current_location, \
#                        dbase=current_gisdbase, flags='c')
#    
#    new_usgs_mapset = gscript.read_command('g.gisenv', get='MAPSET')
#    
#    #work_DIR = current_gisdbase + '/' + current_location + '/' + new_usgs_mapset
#    #print work_DIR
#"""   
    LT_count = 0
    LT_fullpaths = []
    LT_basenames = []
    # Hardcoded until GRASS GUI option implemented
    work_DIR = "/home/zechariah/Downloads/r.in.usgsned_download"
    
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
                LT_fullpaths.append(LT_path)
                LT_basenames.append(LT_base)
                print "Tile {0} of {1}: '{2}' downloaded to '{3}'".format(\
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
    
    print "\n**************************\nNED Data Downloaded\n**************************\n"
    
    if LT_count == 1:
        gscript.run_command('r.import', input = LT_fullpaths, \
                            output = LT_basenames, overwrite=True, \
                            verbose=True)
    if LT_count > 1:
        print "\nPatching composite NED imagery to g.region boundary."
        for r in LT_fullpaths:
            LT_file_name = r.split('/')[-1]
            LT_layer_name = LT_file_name.split('.')[0]
            # Defined earlier in script
            # LT_basenames.append(LT_layer_name)
            gscript.run_command('r.import', input = r,  \
                                output = LT_layer_name, overwrite=True)
        gscript.run_command('r.patch', input=LT_basenames, \
                            output='test_combo_patch.img', overwrite=True)
        print "\nImporting Patched Tile to GRASS GIS."
    
    print "\n****************************\nr.in.usgsned Module Complete\n****************************\n"

if __name__ == "__main__":
    options, flags = gscript.parser()
    main()
