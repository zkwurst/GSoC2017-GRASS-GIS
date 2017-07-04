#!/usr/bin/env python
#-*- coding: utf-8 -*-

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
#************************ANSWER SET FOR TESTING ONLY*********************
#% answer: /home/zechariah/Downloads/r.in.usgsned_download
#% description: Directory for USGS data download and processing
#% guisection: Download Options
#%end

#%option G_OPT_R_OUTPUT
#% key: output_layer
#************************ANSWER SET FOR TESTING ONLY*********************
#% answer: usgs_composite_out
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

import sys
import os
import zipfile
import grass.script as gscript
import urllib
import urllib2
import json

def main():
    # Set GRASS GUI options and flags to python variables
    gui_product = options['product']
    gui_resolution = options['resolution']
    gui_output_dir = options['output_dir']
    gui_output_layer = options['output_layer']
    gui_region = options['region']
    gui_resampling_method = options['resampling_method']
    gui_i_flag = flags['i']
    gui_r_flag = flags['r']
    
    # Data dictionary for NED parameters
    USGS_product_dict = {
            "NED": 
                {"title": "National Elevation Dataset (NED)", 
                 "format": "IMG", 
                 # Need to work on dynamic 'file_string' formatting
                 # Currently hardcoded for NED format in 'zipName' var and others
                 "resolution": {"1 arc-second": "1 x 1 degree", 
                                "1/3 arc-second": "1 x 1 degree", 
                                "1/9 arc-second": "15 x 15 minute"
                                },
                 "srs": "wgs84",
                 "srs_proj4": "+proj=longlat +ellps=GRS80 +datum=NAD83 +nodefs"
                 }}
    
    # Dynamic variables called from USGS data dict
    nav_string = USGS_product_dict[gui_product]
    product_title = nav_string["title"]
    product_format = nav_string["format"]
    product_extents = nav_string["resolution"][gui_resolution]
    product_srs = nav_string["srs"]
    product_proj4 = nav_string["srs_proj4"]
    
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
    
    # Converting to urllib2 will lose this built-in JSON parsing
    try:
        # Query TNM API
        TNM_API_GET = urllib2.urlopen(TNM_API_URL, timeout=12)
        returnJSON = json.load(TNM_API_GET)
        # Parse JSON to return download URL
        tile_APIcount = int(returnJSON['total'])
        dwnld_size = []
        dwnld_URL = []
        dataset_name = []
        tile_titles = []
        if tile_APIcount > 0:
            for tile in returnJSON['items']:
                dwnld_size.append(int(tile['sizeInBytes']))
                dwnld_URL.append(str(tile['downloadURL']))
                tile_titles.append(tile['title'])
                if tile['datasets'][0] not in dataset_name:
                    if len(dataset_name) <= 1:
                        dataset_name.append(str(tile['datasets'][0]))
        if tile_APIcount == 0:
            gscript.fatal("Zero tiles returned. Please check input parameters.")
        total_size = sum(dwnld_size)
        if 6 < len(str(total_size)) < 10:
            total_size_float = total_size * 1e-6
            total_size_str = str("{0:.2f}".format(total_size_float) + " MB")
        if len(str(total_size)) >= 10:
            total_size_float = total_size * 1e-9
            total_size_str = str("{0:.2f}".format(total_size_float) + " GB")
    except urllib2.URLError:
        gscript.fatal("\nUSGS API query has timed out. \nPlease try again.\n")
    
    # Variables created for info display
    if gui_r_flag:
        r_flag = "Remove source tiles after download."
    if not gui_r_flag:
        r_flag = "Keep source tiles after download."
    tile_titles_info = "\n".join(tile_titles)
    
    gproj_info = gscript.parse_command('g.proj', flags='g')
    gproj_datum = gproj_info['datum']
    
    # Formatted return for 'i' flag
    data_info = (
                "\n***************************\n"
                 "r.in.usgs Information Query"
                 "\n***************************\n"
                 "USGS Data requested:\n\t"
                 "Product:\t{0}\n\t"
                 "Resolution:\t{1}\n"
                 "Product Extents:\t{2}\n"
                 "\nInput g.region Parameters:\n"
                 "GRASS SRS:\t{3}\n"
                 "Computational Region:\t{4}\n"
                 "Bounding Box Coords (long/lat [w,s,e,n]): \n\t[{13}]\n"
                 "\nOutput environment:\n"
                 "Output Directory:\t{5}\n"
                 "Output Layer Name:\t{6}\n"
                 "\nUSGS File/s to Download:\n"
                 "Total Download Size:\t{7}\n"
                 "Tile Count:\t{8}\n"
                 "USGS SRS:\t{9}\n"
                 "\nUSGS Tile Titles:\n{10}\n"
                 "\nModule Options:\n"
                 "Resampling:\t{11}\n"
                 "'r' flag:\t{12}\n"
                 "\n************************\n"
                 "r.in.usgs Query Complete"
                 "\n************************\n"
                 ).format(gui_product,
                          gui_resolution,
                          product_extents,
                          gproj_datum,
                          gui_region,
                          gui_output_dir,
                          gui_output_layer,
                          total_size_str,
                          tile_APIcount,
                          product_srs,
                          tile_titles_info,
                          gui_resampling_method,
                          r_flag,
                          str_bbox,
                          )
    gscript.info(data_info)
    
    if gui_i_flag:
        gscript.message("\nTo download data, remove 'i' flag, and rerun r.in.usgs.\n")
        exit()
    
    gscript.message("\nDownloading USGS Data...")
    # If not 'i' flag, download files
    
    LT_count = 0
    LT_fullpaths = []
    LT_basenames = []
    
    work_DIR = gui_output_dir

    
    
    
    try:
        # The following 'for' loop is duplicated in download section
        for url in dwnld_URL:
            zipName = url.split('/')[-1]
            zipSplit = zipName.split('.')[0]
            local_temp = os.path.join(work_DIR, zipName)
            # <2013 naming convention
            if "USGS_NED_" not in zipName:
                zip_sub_split = zipSplit.split('_')[0]
                imgName = zip_sub_split.replace('img','') + ".img"
            # >2013 naming convention
            if "USGS_NED" in zipName:
                imgName = zipSplit.split('_')[3] + ".img"
            LT_rename = os.path.join(work_DIR, imgName)
            
#            if os.path.isfile(LT_rename):
#                if os.stat(LT_rename).st_size <
            
            
            dwnldREQ = urllib2.urlopen(url, timeout=12)
            # Writes ZIP archive to HD without writing entire request to memory
            CHUNK = 16 * 1024
            with open(local_temp, "wb+") as tempZIP:
                while True:
                    chunk = dwnldREQ.read(CHUNK)
                    if not chunk:
                        break
                    tempZIP.write(chunk)        
            tempZIP.close()
            with zipfile.ZipFile(local_temp, "r") as read_ZIP:
                for f in read_ZIP.namelist():
                    if f.endswith(".img"):
                        read_ZIP.extract(f, work_DIR)
                        LT_path = os.path.join(work_DIR, str(f))
                        # Rename variable formatting to tile coords
                        os.rename(LT_path, LT_rename)
            if os.path.exists(LT_rename):
                LT_count += 1
                LT_fullpaths.append(LT_rename)
                temp_count = ("Tile {0} of {1}: '{2}' downloaded to '{3}'").format(
                        LT_count, tile_APIcount, imgName, work_DIR)
                gscript.info(temp_count)
            else:
                gscript.fatal("\nDownload Unsuccesful.")
            # Delete original ZIP archive
            os.remove(local_temp)
    except urllib2.URLError:
        gscript.fatal("\nUSGS download request has timed out. Network or formatting error.")
    
    # Check that downloaded files match expected count
    if LT_count == tile_APIcount:
        temp_down_count = ("\n{0} of {1} tile/s succesfully downloaded.").format(LT_count,
               tile_APIcount)
        gscript.info(temp_down_count)
    else:
        gscript.fatal("Error downloading files. Please retry.")

    # Import and patch tiles into GRASS
    patch_names = []
    for r in LT_fullpaths:
        LT_file_name = r.split('/')[-1]
        LT_layer_name = LT_file_name.split('.')[0]
        patch_names.append(LT_layer_name)
        in_info = ("\nImporting and reprojecting {0}...\n").format(LT_file_name)
        gscript.info(in_info)
        gscript.run_command('r.import', input=r,  \
                                output=LT_layer_name, \
                                extent="region")
    gscript.info("\nImport to GRASS GIS complete.\n")
    if LT_count > 1:
        gscript.run_command('r.patch', input=patch_names, \
                            output=gui_output_layer)
        # Need to catch/understand an Error 4 message
        out_info = ("\nPatched composite layer {0} imported to GRASS GIS.").format(gui_output_layer)
        gscript.info(out_info)

    # Remove source files if 'r' flag active
    if gui_r_flag:
        for f in LT_fullpaths:
            os.remove(f)
        gscript.info("\nSource tiles removed.")
    else:
        src_msg = ("\nSource tiles remain in '{0}'").format(gui_output_dir)
        gscript.info(src_msg)
            
            
    gscript.info(
                 "\n***************************\n"
                 "r.in.usgs Download Complete"
                 "\n***************************\n"
                )

# Cleanup funct needed to handle partial temp files caused by disconnect errors
# def cleanup():
    

if __name__ == "__main__":
    options, flags = gscript.parser()
#    atexit.register(cleanup)
    sys.exit(main())
