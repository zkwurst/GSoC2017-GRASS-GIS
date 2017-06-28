#!/usr/bin/env python
#-*- coding: utf-8 -*-

#"""
#MODULE:     r.in.usgsned
#
#AUTHOR:     Zechariah Krautwurst
#
#MENTORS:    Anna Petrasova
#            Vaclav Petras
#
#PURPOSE:    Download user-requested tiles from USGS NED database.
#
#COPYRIGHT:  (C) 2017 Zechariah Krautwurst and the GRASS Development Team
#            
#            This program is free software under the GNU General Public
#            License (>=v2). Read the file COPYING that comes with GRASS
#            for details.
#            
#VERSION:    Preliminary testing phase. Script imports NED IMG tiles for
#            GRASS GIS locations by computational region coordinates.
#            
#NOTES:      Needs:
#            - Improved formatting, function defs, pep8, etc
#            - GUI refinement
#            - Error handling
#            - Comments/html documentation
#            - Code simplification
#            - Develop further USGS formats
#"""

# GRASS GIS wxPython GUI options and flags

#%module
#% description: Download USGS NED data
#% keyword: raster
#% keyword: NED
#%end

# Need to write rule that does not allow both "i" and "d" flags to be selected

#%flag
#% key: i
#% label: Return USGS data information without downloading files
#% guisection: USGS Data Selection
#%end

#%flag
#% key: d
#% label: Download available USGS data
#% guisection: USGS Data Selection
#%end

#%option
#% key: product
#% required: yes
#% options: NED, other (not supported)
#% answer: NED
#% label: Select USGS Data Product
#% description: Choose which available USGS datasets to query
#% descriptions: NED;National Elevation Dataset
#% guisection: USGS Data Selection
#%end

#%option
#% key: resolution
#% required: yes
#% options: 1 arc-second, 1/3 arc-second, 1/9 arc-second
#% answer: 1/3 arc-second
#% label: NED DEM Resolution
#% description: Available NED DEM resolutions
#% guisection: USGS Data Selection
#%end

#%option G_OPT_M_DIR
#% key: output_dir
#% description: Directory for USGS data download and processing
#% guisection: Download Options
#%end

#%option G_OPT_R_OUTPUT
#% key: output_layer
#% description: Layer name for composite region file from NED tiles
#% guisection: Download Options
#%end

#%option G_OPT_M_REGION
#% key: region
#% label: Computational Region
#% answer: current
#% guisection: Download Options
#%end

#%option
#% key: resampling_method
#% type: string
#% required: no
#% multiple: no
#% options: default,nearest,bilinear,bicubic,lanczos,bilinear_f,bicubic_f,lanczos_f
#% description: Resampling method to use
#% descriptions: default;default method based on product;nearest;nearest neighbor;bilinear;bilinear interpolation;bicubic;bicubic interpolation;lanczos;lanczos filter;bilinear_f;bilinear interpolation with fallback;bicubic_f;bicubic interpolation with fallback;lanczos_f;lanczos filter with fallback
#% answer: default
#% guisection: Download Options
#%end

#%flag
#% key: r
#% label: Remove source imagery after tile download and composite map creation
#% description: Remove downloaded source tiles and composite raster
#% guisection: Download Options
#%end

# will convert script to use urllib2 to avoid adding "requests" dependency
import requests # pip install requests
import sys
import os
import zipfile
import grass.script as gscript
import urllib

def main():
    # Set GRASS GUI options and flags to python variables
    gui_product = options['product']
    gui_resolution = options['resolution']
    gui_output_dir = options['output_dir']
    gui_output_layer = options['output_layer']
    gui_region = options['region']
    gui_resampling_method = options['resampling_method']
    gui_i_flag = flags['i']
    gui_d_flag = flags['d']
    gui_r_flag = flags['r']
    
    # Data dictionary for NED parameters
    USGS_product_dict = [{"product": 
            {"NED": 
                {"title": "National Elevation Dataset (NED)", 
                 "format": "IMG", 
                 # Need to work on dynamic 'file_string' formatting
                 # Currently hardcoded for NED format around line 237
                 "file_string": "'img{0}_13.img'",
                 "resolution": {"1 arc-second": "1 x 1 degree", 
                                "1/3 arc-second": "1 x 1 degree", 
                                "1/9 arc-second": "15 x 15 minute"
                                },
                 "srs": "nad83",
                 "srs_proj4": "+proj=longlat +ellps=GRS80 +datum=NAD83 +nodefs"
                 }}}]
    
    # Dynamic variables called from USGS data dict
    nav_string = USGS_product_dict[0]["product"][gui_product]
    product_title = nav_string["title"]
    product_format = nav_string["format"]
    product_format_string = nav_string["file_string"]
    product_extents = nav_string["resolution"][gui_resolution]
    product_srs = nav_string["srs"]
    product_proj4 = nav_string["srs_proj4"]

    print "\n************************\nNED Data Download Module\n************************"
    
    # Get coordinates for current GRASS computational region and convert to USGS SRS
    gregion = gscript.region()
    min_coords = gscript.read_command('m.proj', coordinates=(gregion['w'], gregion['s']),
                                                proj_out=product_proj4, separator='comma',
                                                flags='d')
    max_coords = gscript.read_command('m.proj', coordinates=(gregion['e'], gregion['n']),
                                                proj_out=product_proj4, separator='comma',
                                                flags='d')
    min_list = min_coords.split(',')[:2]
    max_list = max_coords.split(',')[:2]
    list_bbox = min_list + max_list
    str_bbox = ",".join((str(coord) for coord in list_bbox))

    # Format variables for TNM API call
    gui_prod_str = product_title + " " + gui_resolution
    datasets = urllib.quote_plus(gui_prod_str)
    prodFormat = urllib.quote_plus(product_format)
    
    # Create TNM API URL
    base_TNM = "https://viewer.nationalmap.gov/tnmaccess/api/products?"
    datasets_TNM = "datasets={0}".format(datasets)
    bbox_TNM = "&bbox={0}".format(str_bbox)
    prodFormats_TNM = "&prodFormats={0}".format(prodFormat)
    TNM_API_URL = base_TNM + datasets_TNM + bbox_TNM + prodFormats_TNM

    # Query TNM API for data availability
    try:
        # Converting to urllib2 will lose this built-in JSON parsing
        TNM_API_GET = requests.get(TNM_API_URL, timeout=12)
        returnJSON = TNM_API_GET.json()
        # Parse JSON to return download URL
        tile_APIcount = int(returnJSON['total'])
        dwnld_size = []
        dwnld_URL = []
        dataset_name = []
        if tile_APIcount > 0:
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
    except requests.exceptions.Timeout:
        print ("\nUSGS API query has timed out. \nPlease try again.\n")
        sys.exit(1)
    if gui_i_flag:
        # print info to GRASS message
        # print instructions to run again with "d" flag for download
        sys.exit(1)
    
    # Download results from TNM API query
    if gui_d_flag:
        LT_count = 0
        LT_fullpaths = []
        LT_basenames = []
        work_DIR = gui_output_dir
        try:
            for url in dwnld_URL:
                dwnldREQ = requests.get(url, timeout=12, stream=True)
                zipName = url.split('/')[-1]
                local_temp = work_DIR + '/' + zipName
                zipSplit = zipName.split('.')[0]
                # This step needs to be refined/standardized. I'm not sure 
                # if different datasets have different naming conventions 
                # for their .img files or other file types.
                # imgName = product_format_string.format(zipSplit)
                imgName = "img" + zipSplit + "_13.img"
                LT_base = imgName.split('.')[0]
                # Write ZIP archive to HD without writing entire request to memory
                with open(local_temp, "wb+") as tempZIP:
                    for chunk in dwnldREQ.iter_content(chunk_size=1024):
                        if chunk:
                            tempZIP.write(chunk)
                # Index into zip dir to retrieve and save IMG file
                # vsizip.vsicurl gdal tools?
                with zipfile.ZipFile(local_temp, "r") as read_ZIP:
                    for f in read_ZIP.namelist():
                        if str(f) == imgName:
                            read_ZIP.extract(f, work_DIR) 
                # Delete original ZIP archive
                os.remove(local_temp)
                LT_path = work_DIR + '/' + imgName
                if os.path.exists(LT_path):
                    LT_count += 1
                    LT_fullpaths.append(LT_path)
                    LT_basenames.append(LT_base)
                    print "Tile {0} of {1}: '{2}' downloaded to '{3}'".format(\
                            LT_count, tile_APIcount, imgName, work_DIR)
                else:
                    print "Download Unsuccesful."
                    sys.exit(1)
        except requests.exceptions.Timeout:
            print "\nUSGS download request has timed out. Network or formatting error.\n"
            sys.exit(1)
        
        # Check that downloaded files match expected count
        if LT_count == tile_APIcount:
            print "\n{0} of {1} tiles succesfully downloaded.".format(LT_count,\
                   tile_APIcount)
            print "\n************************************\nNED Data Download Complete\n************************************\n"
        
        # Import single file into GRASS
        if LT_count == 1:
            gscript.run_command('r.import', input = LT_fullpaths, \
                                output = LT_basenames, overwrite=True, \
                                verbose=True)
        # Import and patch multiple tiles into GRASS
        if LT_count > 1:
            for r in LT_fullpaths:
                LT_file_name = r.split('/')[-1]
                LT_layer_name = LT_file_name.split('.')[0]
                gscript.run_command('r.import', input = r,  \
                                    output = LT_layer_name, \
                                    extent="region")
            gscript.run_command('r.patch', input=LT_basenames, \
                                output=gui_output_layer)
            print "\nPatched composite layer imported to GRASS GIS."
    
    print "\n****************************\nr.in.usgsned Module Complete\n****************************\n"

if __name__ == "__main__":
    options, flags = gscript.parser()
    main()
