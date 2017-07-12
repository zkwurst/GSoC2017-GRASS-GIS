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
#            - Comments/html documentation
#            - Code simplification
#            - Develop further USGS formats

#%module
#% description: Download USGS NED data
#% keyword: raster
#% keyword: NED
#%end

#%flag
#% key: i
#% label: Return USGS data information without downloading files
#% guisection: USGS Data Selection
#%end

#%option
#% key: product
#% required: yes
#% options: ned, nlcd, ntd, small-scale
#% answer: ned
#% label: Select USGS Data Product
#% description: Choose which available USGS datasets to query
#% descriptions: ned;National Elevation Dataset,nlcd;National Land Cover Dataset
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
#% key: k
#% label: Keep source imagery after tile download and composite map creation
#% description: Keep downloaded source tiles and GRASS map layers
#% guisection: Download Options
#%end

import sys
import os
import zipfile
import grass.script as gscript
import urllib
import urllib2
import json
import atexit

cleanup_list = []

def cleanup():
    for f in cleanup_list:
        if os.path.exists(f):
            os.remove(f)

def main():
    # Set GRASS GUI options and flags to python variables
    gui_product = options['product']
    gui_resolution = options['resolution']
    gui_output_layer = options['output_layer']
    gui_region = options['region']
    gui_resampling_method = options['resampling_method']
    gui_i_flag = flags['i']
    gui_k_flag = flags['k']
    work_dir = options['output_dir']

    # Hard-coded data dictionary for NED parameters
    USGS_product_dict = {
            "ned": 
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
    product_SRS = nav_string["srs"]
    product_PROJ4 = nav_string["srs_proj4"]

    # Get coordinates for current GRASS computational region and convert to USGS SRS
    gregion = gscript.region()
    min_coords = gscript.read_command('m.proj', coordinates=(gregion['w'], gregion['s']),
                                                proj_out=product_PROJ4, separator='comma',
                                                flags='d')
    max_coords = gscript.read_command('m.proj', coordinates=(gregion['e'], gregion['n']),
                                                proj_out=product_PROJ4, separator='comma',
                                                flags='d')
    min_list = min_coords.split(',')[:2]
    max_list = max_coords.split(',')[:2]
    list_bbox = min_list + max_list
    str_bbox = ",".join((str(coord) for coord in list_bbox))

    # Format variables for TNM API call
    gui_prod_str = product_title + " " + gui_resolution
    datasets = urllib.quote_plus(gui_prod_str)
    prod_format = urllib.quote_plus(product_format)

    # Create TNM API URL
    base_TNM = "https://viewer.nationalmap.gov/tnmaccess/api/products?"
    datasets_TNM = "datasets={0}".format(datasets)
    bbox_TNM = "&bbox={0}".format(str_bbox)
    prod_format_TNM = "&prodFormats={0}".format(prod_format)
    TNM_API_URL = base_TNM + datasets_TNM + bbox_TNM + prod_format_TNM

    gscript.info("\nTNM API Query URL:\t{0}\n".format(TNM_API_URL))

    try:
        # Query TNM API
        TNM_API_GET = urllib2.urlopen(TNM_API_URL, timeout=12)
    except urllib2.URLError:
        gscript.fatal("\nUSGS API query has timed out. \nPlease try again.\n")

    try:
        # Parse return JSON object
        return_JSON = json.load(TNM_API_GET)
    except:
        gscript.fatal("\nUnable to load USGS JSON object.")

    tile_API_count = int(return_JSON['total'])
    dwnld_size = []
    total_size = sum(dwnld_size)
    dwnld_URL = []
    dataset_name = []
    tile_titles = []
    if tile_API_count > 0:
        while True:
            for tile in return_JSON['items']:
                TNM_title = tile['title']
                TNM_tile_URL = str(tile['downloadURL'])
                TNM_tile_size = int(tile['sizeInBytes'])
                TNM_zip_name = TNM_tile_URL.split('/')[-1]
                pre_local_zip = os.path.join(work_dir, TNM_zip_name)
                if not os.path.exists(pre_local_zip):
                    dwnld_URL.append(TNM_tile_URL)
                    dwnld_size.append(TNM_tile_size)
                    tile_titles.append(TNM_title)
                    if tile['datasets'][0] not in dataset_name:
                        if len(dataset_name) <= 1:
                            dataset_name.append(str(tile['datasets'][0]))
                else:
                    existing_LZ_size = os.path.getsize(pre_local_zip)
                    if existing_LZ_size != TNM_tile_size:
                        cleanup_list.append(pre_local_zip)
                        break
            if cleanup_list:
                cleanup_count = len(cleanup_list)
                cleanup_error = "\n{0} incomplete existing local ZIP archive/s were removed. Module information includes replacement files.\n".format(cleanup_count)
                gscript.warning(cleanup_error)
                cleanup()
                break
    elif tile_API_count == 0:
        gscript.fatal("Zero tiles available for given input parameters.")
            
    if 6 < len(str(total_size)) < 10:
        total_size_float = total_size * 1e-6
        total_size_str = str("{0:.2f}".format(total_size_float) + " MB")
    if len(str(total_size)) >= 10:
        total_size_float = total_size * 1e-9
        total_size_str = str("{0:.2f}".format(total_size_float) + " GB")

    # Variables created for info display
    if gui_k_flag:
        k_flag = "'k' flag set. KEEP source files after download."
    if not gui_k_flag:
        k_flag = "'k' flag NOT set. REMOVE source files after download."
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
                 "'k' flag:\t{12}\n"
                 "\n************************\n"
                 "r.in.usgs Query Complete"
                 "\n************************\n"
                 ).format(gui_product,
                          gui_resolution,
                          product_extents,
                          gproj_datum,
                          gui_region,
                          work_dir,
                          gui_output_layer,
                          total_size_str,
                          tile_API_count,
                          product_SRS,
                          tile_titles_info,
                          gui_resampling_method,
                          k_flag,
                          str_bbox,
                          )

    gscript.info(data_info)
    if gui_i_flag:
        gscript.fatal("\nTo download USGS data, remove 'i' flag, and rerun r.in.usgs.\n")


    # USGS data download process
    gscript.message("\nDownloading USGS Data...")
    TNM_count = len(dwnld_URL)
    LZ_count = 0
    LT_count = 0
    LT_paths = []
    LZ_paths = []
    patch_names = []
    
    # Download ZIP files
    for url in dwnld_URL:
        zip_name = url.split('/')[-1]
        local_zip = os.path.join(work_dir, zip_name)

        try:
            dwnld_req = urllib2.urlopen(url, timeout=12)
        except urllib2.URLError:
            gscript.fatal("\nUSGS download request has timed out. Network or formatting error.")
        try:
            CHUNK = 16 * 1024
            with open(local_zip, "wb+") as temp_zip:
                while True:
                    chunk = dwnld_req.read(CHUNK)
                    if not chunk:
                        break
                    temp_zip.write(chunk)        
            temp_zip.close()
            if os.path.exists(local_zip):
                LZ_count += 1
                LZ_paths.append(local_zip)
                zip_complete = "\nDownload {0} of {1}: COMPLETE".format(
                        LZ_count, TNM_count)
                gscript.message(zip_complete)
        except:
            zip_failed = "\nDownload {0} of {1}: FAILED".format(
                        LZ_count, TNM_count)
            gscript.message(zip_failed)
            continue
    

    for z in LZ_paths:
        # Extract tiles from ZIP archives
        try:
            with zipfile.ZipFile(z, "r") as read_zip:
                for f in read_zip.namelist():
                        if f.endswith(".img"):
                            img_name = f
                            local_tile = os.path.join(work_dir, str(f))
                            read_zip.extract(f, work_dir)
            if os.path.exists(local_tile):
                LT_count += 1
                LT_paths.append(local_tile)
        except:
            cleanup_list.append(local_tile)
            gscript.fatal("Unable to locate or extract IMG file from ZIP archive.")

    for t in LT_paths:
        LT_file_name = t.split('/')[-1]
        LT_layer_name = LT_file_name.split('.')[0]
        patch_names.append(LT_layer_name)
        in_info = ("\nImporting and reprojecting {0}...\n").format(LT_file_name)
        gscript.info(in_info)
        try:
            gscript.run_command('r.import', input=LT_file_name,
                                output=LT_layer_name,
                                extent="region")
            in_complete = ("Computational region from '{0}' imported to GRASS GIS").format(img_name)
            gscript.info(in_complete)
            if not gui_k_flag:
                cleanup_list.append(t)
        except:
            in_error = ("\nUnable to import '{0}'\n").format(LT_file_name)
            gscript.fatal(in_error)

    if len(LT_count) > 1:
        try:
            gscript.run_command('r.patch', input=patch_names,
                                output=gui_output_layer)
            out_info = ("\nPatched composite layer '{0}' added to GRASS GIS.").format(gui_output_layer)
            gscript.info(out_info)
            gscript.run_command('g.remove', type='raster',
                                name=patch_names,
                                flags='f')
        except:
            gscript.fatal("\nUnable to patch tiles.\n")
    
    # Check that downloaded files match expected count
    if LT_count == tile_API_count:
        temp_down_count = ("\n{0} of {1} tile/s succesfully downloaded.").format(LT_count,
               tile_API_count)
        gscript.info(temp_down_count)
    else:
        gscript.fatal("Error downloading files. Please retry.")

    # Remove source files if 'r' flag active
    if gui_k_flag: 
        src_msg = ("\n'k' flag selected: Source tiles remain in '{0}'").format(work_dir)
        gscript.info(src_msg)

    gscript.info(
                 "\n***************************\n"
                 "r.in.usgs Download Complete"
                 "\n***************************\n"
                )

if __name__ == "__main__":
    options, flags = gscript.parser()
    atexit.register(cleanup)
    sys.exit(main())
