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
#VERSION:    [STABLE] r.in.usgsned
#
#COPYRIGHT:  (C) 2017 Zechariah Krautwurst and the GRASS Development Team
#
#            This program is free software under the GNU General Public
#            License (>=v2). Read the file COPYING that comes with GRASS
#            for details.

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
#% key: output_directory
#% required: no
#% description: Directory for USGS data download and processing
#% guisection: Download Options
#%end

#%option G_OPT_R_OUTPUT
#% key: output
#% required: no
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

#%rules
#% required: output, -i
#%end

import sys
import os
import zipfile
import grass.script as gscript
import urllib
import urllib2
import json
import atexit

from grass.exceptions import CalledModuleError


cleanup_list = []


def cleanup():
    for f in cleanup_list:
        if os.path.exists(f):
            os.remove(f)


def main():
    # Set GRASS GUI options and flags to python variables
    gui_product = options['product']
    gui_resolution = options['resolution']
    gui_output_layer = options['output']
    gui_resampling_method = options['resampling_method']
    gui_i_flag = flags['i']
    gui_k_flag = flags['k']
    work_dir = options['output_directory']

    # Hard-coded data dictionary for NED parameters
    USGS_product_dict = {
            "ned":
                {"title": "National Elevation Dataset (NED)",
                 "format": "IMG",
                 # Need to work on dynamic 'file_string' formatting
                 # Currently hardcoded for NED format in 'zipName' var and others
                 # defined resolution in degrees, meters, and feet
                 "resolution": {"1 arc-second": (1. / 3600, 30, 100),
                                "1/3 arc-second": (1. / 3600 / 3, 10, 30),
                                "1/9 arc-second": (1. / 3600 / 9, 3, 10)
                                },
                 "srs": "wgs84",
                 "srs_proj4": "+proj=longlat +ellps=GRS80 +datum=NAD83 +nodefs",
                 "interpolation": "bilinear"
                 }}

    # Dynamic variables called from USGS data dict
    nav_string = USGS_product_dict[gui_product]
    product_title = nav_string["title"]
    product_format = nav_string["format"]
    product_resolution = nav_string["resolution"][gui_resolution]
    product_SRS = nav_string["srs"]
    product_PROJ4 = nav_string["srs_proj4"]

    # current units
    proj = gscript.parse_command('g.proj', flags='g')
    if gscript.locn_is_latlong:
        product_resolution = product_resolution[0]
    elif float(proj['meters']) == 1:
        product_resolution = product_resolution[1]
    else:
        # we assume feet
        product_resolution = product_resolution[2]

    if gui_resampling_method == 'default':
        gui_resampling_method = nav_string['interpolation']
        gscript.verbose(_("The default resampling method for product {product} is {res}").format(product=gui_product,
                        res=gui_resampling_method))

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

    gscript.verbose("TNM API Query URL:\t{0}".format(TNM_API_URL))

    try:
        # Query TNM API
        TNM_API_GET = urllib2.urlopen(TNM_API_URL, timeout=12)
    except urllib2.URLError:
        gscript.fatal("USGS TNM API query has timed out. Check network configuration. Please try again.")

    try:
        # Parse return JSON object
        return_JSON = json.load(TNM_API_GET)
    except:
        gscript.fatal("Unable to load USGS JSON object.")

    tile_API_count = int(return_JSON['total'])
    if tile_API_count > 0:
        dwnld_size = []
        dwnld_URL = []
        dataset_name = []
        tile_titles = []
        zip_names = []
        exist_zip_list = []
        for tile in return_JSON['items']:
            TNM_title = tile['title']
            TNM_tile_URL = str(tile['downloadURL'])
            TNM_tile_size = int(tile['sizeInBytes'])
            TNM_zip_name = TNM_tile_URL.split('/')[-1]
            pre_local_zip = os.path.join(work_dir, TNM_zip_name)
            zip_exists = os.path.exists(pre_local_zip)
            if zip_exists:
                existing_LZ_size = os.path.getsize(pre_local_zip)
                if existing_LZ_size != TNM_tile_size:
                    cleanup_list.append(pre_local_zip)
                else:
                    exist_zip_list.append(pre_local_zip)
                    cleanup_msg = "{0} existing ZIP archive(s) will be used by module.".format(len(exist_zip_list))
                    gscript.verbose(cleanup_msg)
                    dwnld_URL.append(TNM_tile_URL)
                    dwnld_size.append(TNM_tile_size)
                    tile_titles.append(TNM_title)
                    zip_names.append(TNM_zip_name)
                    if tile['datasets'][0] not in dataset_name:
                        if len(dataset_name) <= 1:
                            dataset_name.append(str(tile['datasets'][0]))
            if not zip_exists:
                dwnld_URL.append(TNM_tile_URL)
                dwnld_size.append(TNM_tile_size)
                tile_titles.append(TNM_title)
                zip_names.append(TNM_zip_name)
                if tile['datasets'][0] not in dataset_name:
                    if len(dataset_name) <= 1:
                        dataset_name.append(str(tile['datasets'][0]))
        if cleanup_list:
            cleanup_msg = "{0} existing incomplete ZIP archive(s) detected and removed. Run module again.".format(len(cleanup_list))
            gscript.fatal(cleanup_msg)

    elif tile_API_count == 0:
        gscript.fatal("Zero tiles available for given input parameters.")

    total_size = sum(dwnld_size)
    len_total_size = len(str(total_size))

    if 6 < len_total_size < 10:
        total_size_float = total_size * 1e-6
        total_size_str = str("{0:.2f}".format(total_size_float) + " MB")
    if len_total_size >= 10:
        total_size_float = total_size * 1e-9
        total_size_str = str("{0:.2f}".format(total_size_float) + " GB")

    # Variables created for info display
    if gui_k_flag:
        k_flag = "'k' flag set. KEEP source files after download."
    if not gui_k_flag:
        k_flag = "'k' flag NOT set. REMOVE source files after download."
    tile_titles_info = "\n".join(tile_titles)

    # Formatted return for 'i' flag
    data_info = (
                 "USGS file(s) to download:",
                 "-------------------------",
                 "Total download size:\t{size}",
                 "Tile count:\t{count}",
                 "USGS SRS:\t{srs}",
                 "USGS tile titles:\n{tile}",
                 "-------------------------",
                 )
    data_info = '\n'.join(data_info).format(size=total_size_str,
                                            count=tile_API_count,
                                            srs=product_SRS,
                                            tile=tile_titles_info)

    if gui_i_flag:
        gscript.info(data_info)
        gscript.info("To download USGS data, remove <i> flag, and rerun r.in.usgs.")
        return
    else:
        gscript.verbose(data_info)

    # USGS data download process
    gscript.message("Downloading USGS Data...")
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
            download_bytes = int(dwnld_req.info()['Content-Length'])
        except urllib2.URLError:
            gscript.fatal("USGS download request has timed out. Network or formatting error.")
        try:
            CHUNK = 16 * 1024
            with open(local_zip, "wb+") as temp_zip:
                count = 0
                steps = int(download_bytes / CHUNK) + 1
                while True:
                    chunk = dwnld_req.read(CHUNK)
                    gscript.percent(count, steps, 10)
                    count += 1
                    if not chunk:
                        break
                    temp_zip.write(chunk)
            temp_zip.close()
            if os.path.exists(local_zip):
                LZ_count += 1
                LZ_paths.append(local_zip)
                zip_complete = "Download {0} of {1}: COMPLETE".format(
                        LZ_count, TNM_count)
                gscript.info(zip_complete)
        except StandardError:
            zip_failed = "Download {0} of {1}: FAILED".format(
                        LZ_count, TNM_count)
            gscript.fatal(zip_failed)

    for z in LZ_paths:
        # Extract tiles from ZIP archives
        try:
            with zipfile.ZipFile(z, "r") as read_zip:
                for f in read_zip.namelist():
                        if f.endswith(".img"):
                            local_tile = os.path.join(work_dir, str(f))
                            read_zip.extract(f, work_dir)
            if os.path.exists(local_tile):
                LT_count += 1
                LT_paths.append(local_tile)
        except:
            cleanup_list.append(local_tile)
            gscript.fatal("Unable to locate or extract IMG file from ZIP archive.")

    for t in LT_paths:
        LT_file_name = os.path.basename(t)
        LT_layer_name = os.path.splitext(LT_file_name)[0]
        patch_names.append(LT_layer_name)
        in_info = ("Importing and reprojecting {0}...").format(LT_file_name)
        gscript.info(in_info)
        try:
            gscript.run_command('r.import', input=t, output=LT_layer_name,
                                resolution='value', resolution_value=product_resolution,
                                extent="region", resample=gui_resampling_method)
            if not gui_k_flag:
                cleanup_list.append(t)
        except CalledModuleError:
            in_error = ("Unable to import '{0}'").format(LT_file_name)
            gscript.fatal(in_error)

    if LT_count > 1:
        try:
            gscript.use_temp_region()
            # set the resolution
            gscript.run_command('g.region', res=product_resolution, flags='a')
            gscript.run_command('r.patch', input=patch_names,
                                output=gui_output_layer)
            gscript.del_temp_region()
            out_info = ("Patched composite layer '{0}' added").format(gui_output_layer)
            gscript.verbose(out_info)
            if not gui_k_flag:
                gscript.run_command('g.remove', type='raster',
                                    name=patch_names, flags='f')
        except CalledModuleError:
            gscript.fatal("Unable to patch tiles.")
    elif LT_count == 1:
        gscript.run_command('g.rename', raster=(patch_names[0], gui_output_layer))

    # Check that downloaded files match expected count
    if LT_count == tile_API_count:
        temp_down_count = ("{0} of {1} tile/s succesfully imported.").format(LT_count,
                           tile_API_count)
        gscript.info(temp_down_count)
    else:
        gscript.fatal("Error downloading files. Please retry.")

    # Remove source files if 'r' flag active
    if gui_k_flag:
        src_msg = ("<k> flag selected: Source tiles remain in '{0}'").format(work_dir)
        gscript.info(src_msg)

    # set appropriate color table
    if gui_product == 'ned':
        gscript.run_command('r.colors', map=gui_output_layer, color='elevation')


if __name__ == "__main__":
    options, flags = gscript.parser()
    atexit.register(cleanup)
    sys.exit(main())
