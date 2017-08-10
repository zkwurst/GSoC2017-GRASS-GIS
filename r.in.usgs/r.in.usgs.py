#!/usr/bin/env python
#-*- coding: utf-8 -*-

#MODULE:     r.in.usgs
#
#AUTHOR:     Zechariah Krautwurst
#
#MENTORS:    Anna Petrasova
#            Vaclav Petras
#
#PURPOSE:    Download user-requested products from USGS database.
#
#VERSION:    [DEV] r.in.usgs
#
#COPYRIGHT:  (C) 2017 Zechariah Krautwurst and the GRASS Development Team
#
#            This program is free software under the GNU General Public
#            License (>=v2). Read the file COPYING that comes with GRASS
#            for details.

#%module
#% description: Download USGS data
#% keyword: raster
#% keyword: USGS
#%end

#%flag
#% key: i
#% label: Return USGS data information without downloading files
#% guisection: USGS Data Selection
#%end

#%option
#% key: product
#% required: yes
#% options: ned, nlcd, naip
#% label: USGS data product
#% description: Choose which available USGS data product to query
#% guisection: USGS Data Selection
#%end

#%option
#% key: ned_dataset
#% required: no
#% options: 1 arc-second, 1/3 arc-second, 1/9 arc-second
#% answer: 1/3 arc-second
#% label: NED dataset
#% description: Choose which available USGS dataset to query
#% guisection: ned
#%end

#%option
#% key: nlcd_dataset
#% required: no
#% options: National Land Cover Database (NLCD) - 2001, National Land Cover Database (NLCD) - 2006', National Land Cover Database (NLCD) - 2011
#% answer: National Land Cover Database (NLCD) - 2011
#% label: NLCD dataset
#% description: Choose which available NLCD dataset to query
#% guisection: nlcd
#%end

#%option
#% key: nlcd_subset
#% required: no
#% options: Percent Developed Imperviousness, Percent Tree Canopy, Land Cover
#% answer: Land Cover
#% label: NLCD subset
#% description: Choose which available NLCD subset to query
#% guisection: nlcd
#%end

#%option
#% key: naip_dataset
#% required: no
#% options: USDA National Agriculture Imagery Program (NAIP)
#% answer: USDA National Agriculture Imagery Program (NAIP)
#% label: NAIP dataset
#% description: Choose which available NAIP dataset to query
#% guisection: naip
#%end

#%option G_OPT_M_DIR
#% key: output_directory
#% required: yes
#% description: Directory for USGS data download and processing
#% guisection: Download Options
#%end

#%option G_OPT_R_OUTPUT
#% key: output
#% required: yes
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

def main():

    usgs_product_dict = {
        "ned":{
                'product':'National Elevation Dataset (NED)',
                'dataset':{
                        '1 arc-second': (1. / 3600, 30, 100),
                        '1/3 arc-second': (1. / 3600 / 3, 10, 30),
                        '1/9 arc-second': (1. / 3600 / 9, 3, 10)
                        },
                'subset':{},
                'extent':{
                        '1 x 1 degree',
                        '15 x 15 minute'
                        },
                'format':'IMG',
                'extension':'img',
                'zip':True,
                'srs':'wgs84',
                'srs_proj4':"+proj=longlat +ellps=GRS80 +datum=NAD83 +nodefs",
                'interpolation':'bilinear',
                'url_split':'/'
                },
        "nlcd":{
                'product':'National Land Cover Database (NLCD)',
                'dataset':{
                        'National Land Cover Database (NLCD) - 2001',
                        'National Land Cover Database (NLCD) - 2006',
                        'National Land Cover Database (NLCD) - 2011'
                        },
                'subset':{
                        'Percent Developed Imperviousness', 
                        'Percent Tree Canopy',
                        'Land Cover'
                        },
                'extent':{
                        '3 x 3 degree'
                        },
                'format':'GEOTIFF',
                'extension':'tif',
                'zip':True,
                'srs':'wgs84',
                'srs_proj4':"+proj=longlat +ellps=GRS80 +datum=NAD83 +nodefs",
                'interpolation':'bilinear',
                'url_split':'&FNAME='
                },
        "naip":{
                'product':'USDA National Agriculture Imagery Program (NAIP)',
                'dataset':{
                        'Imagery - 1 meter (NAIP)':{()}
                        },
                'subset':{},
                'extent':{
                        '3.75 x 3.75 minute',
                        },
                'format':'JPEG2000',
                'extension':'jp2',
                'zip':False,
                'srs':'wgs84',
                'srs_proj4':"+proj=longlat +ellps=GRS80 +datum=NAD83 +nodefs",
                'interpolation':'bilinear',
                'url_split':'/'
                }}

    # Set GRASS GUI options and flags to python variables
    gui_product = options['product']
    
    # Variables from USGS product dict
    nav_string = usgs_product_dict[gui_product]
    product = nav_string['product']
    product_format = nav_string['format']
    product_extension = nav_string['extension']
    product_zip = nav_string['zip']
    product_srs = nav_string['srs']
    product_proj4 = nav_string['srs_proj4']
    product_interpolation = nav_string['interpolation']
    product_url_split = nav_string['url_split']


    if gui_product == 'ned':
        gui_dataset = options['ned_dataset']
        product_tag = product + " " + gui_dataset
        gui_subset = None
    if gui_product == 'nlcd':
        gui_dataset = options['nlcd_dataset']
        product_tag = gui_dataset
        gui_subset = options['nlcd_subset']
    if gui_product == 'naip':
        gui_dataset = options['naip_dataset']
        product_tag = nav_string['product']
        gui_subset = None

    gui_output_layer = options['output']
    gui_resampling_method = options['resampling_method']
    gui_i_flag = flags['i']
    gui_k_flag = flags['k']
    work_dir = options['output_directory']
    
    # current units
    try:
        proj = gscript.parse_command('g.proj', flags='g')
        if gscript.locn_is_latlong():
            product_resolution = nav_string['dataset'][gui_dataset][0]
        elif float(proj['meters']) == 1:
            product_resolution = nav_string['dataset'][gui_dataset][1]
        else:
            # we assume feet
            product_resolution = nav_string['dataset'][gui_dataset][2]
    except TypeError:
        product_resolution = False

    if gui_resampling_method == 'default':
        gui_resampling_method = nav_string['interpolation']
        gscript.verbose(_("The default resampling method for product {product} is {res}").format(product=gui_product,
                        res=product_interpolation))

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
    
    gui_prod_str = str(product_tag)
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
    
    # adds zip properties to needed lists for download
    def down_list():
        dwnld_url.append(TNM_tile_URL)
        dwnld_size.append(TNM_tile_size)
        tile_titles.append(TNM_title)
        if tile['datasets'][0] not in dataset_name:
            if len(dataset_name) <= 1:
                dataset_name.append(str(tile['datasets'][0]))

    tile_API_count = int(return_JSON['total'])
    size_diff_tolerance = 5
    if tile_API_count > 0:
        dwnld_size = []
        dwnld_url = []
        dataset_name = []
        tile_titles = []
        exist_dwnld_size = 0
        exist_dwnld_url = []
        exist_tile_titles = []
        exist_file_list = []
        for tile in return_JSON['items']:
            TNM_title = tile['title']
            TNM_tile_URL = str(tile['downloadURL'])
            TNM_tile_size = int(tile['sizeInBytes'])
            TNM_file_name = TNM_tile_URL.split(product_url_split)[-1]
            pre_local_file = os.path.join(work_dir, TNM_file_name)
            file_exists = os.path.exists(pre_local_file)
            if file_exists:
                existing_LF_size = os.path.getsize(pre_local_file)
                if abs(existing_LF_size - TNM_tile_size) > size_diff_tolerance:
                    cleanup_list.append(pre_local_file)
                    down_list()
                else:
                    exist_file_list.append(pre_local_file)
                    exist_tile_titles.append(TNM_title)
                    exist_dwnld_url.append(TNM_tile_URL)
                    exist_dwnld_size += TNM_tile_size
            if gui_subset:
                if gui_subset in TNM_title:
                    down_list()
                else:
                    pass
            else:
                down_list()

        tile_needed_count = len(dwnld_url)
        exist_file_count = len(exist_tile_titles)
        tile_download_count = tile_needed_count - exist_file_count
        
        for t in exist_tile_titles:
            if t in tile_titles:
                tile_titles.remove(t)
        for url in exist_dwnld_url:
            if url in dwnld_url:
                dwnld_url.remove(url)


    elif tile_API_count == 0:
        gscript.fatal("Zero tiles available for given input parameters.")

    if exist_file_list:
        exist_msg = "\n{0} complete files/archive(s) exist locally and will be used by module.".format(len(exist_file_list))
        gscript.message(exist_msg)
    if cleanup_list:
        cleanup_msg = "\n{0} existing incomplete ZIP archive(s) detected and removed. Run module again.".format(len(cleanup_list))
        gscript.fatal(cleanup_msg)
    
    if dwnld_size:
        total_size = sum(dwnld_size) - exist_dwnld_size
        len_total_size = len(str(total_size))
        if 6 < len_total_size < 10:
            total_size_float = total_size * 1e-6
            total_size_str = str("{0:.2f}".format(total_size_float) + " MB")
        if len_total_size >= 10:
            total_size_float = total_size * 1e-9
            total_size_str = str("{0:.2f}".format(total_size_float) + " GB")
    else:
        total_size_str = '0'

    # Variables created for info display
    if gui_k_flag:
        k_flag = "'k' flag set. KEEP source files after download."
    else:
        k_flag = "'k' flag NOT set. REMOVE source files after download."
    # Prints 'none' if all tiles available locally
    if tile_titles:
        tile_titles_info = "\n".join(tile_titles)
    else:
        tile_titles_info = 'none'

    # Formatted return for 'i' flag
    if tile_download_count == 0:
        data_info = "USGS file(s) to download: NONE"
    else:
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
                                                count=tile_download_count,
                                                srs=product_srs,
                                                tile=tile_titles_info)

    if gui_i_flag:
        gscript.info(data_info)
        gscript.info("To download USGS data, remove <i> flag, and rerun r.in.usgs.")
        return
    else:
        gscript.verbose(data_info)

    # USGS data download process
    if tile_download_count == 0:
        gscript.message("Extracting existing USGS Data...")
    else:
        gscript.message("Downloading USGS Data...")

    TNM_count = len(dwnld_url)
    LT_count = 0
    LT_paths = []
    LZ_paths = []
    patch_names = []

    print "TNM_count = " + str(TNM_count)
    # Download files
    for url in dwnld_url:
        file_name = url.split(product_url_split)[-1]
        print "file_name = " + file_name
        local_file = os.path.join(work_dir, file_name)
        try:
            dwnld_req = urllib2.urlopen(url, timeout=12)
            download_bytes = int(dwnld_req.info()['Content-Length'])
            CHUNK = 16 * 1024
            with open(local_file, "wb+") as temp_file:
                count = 0
                steps = int(download_bytes / CHUNK) + 1
                while True:
                    chunk = dwnld_req.read(CHUNK)
                    gscript.percent(count, steps, 10)
                    count += 1
                    if not chunk:
                        break
                    temp_file.write(chunk)
            temp_file.close()
            LT_count += 1
            LT_paths.append(local_file)
            file_complete = "Download {0} of {1}: COMPLETE".format(
                    LT_count, TNM_count)
            gscript.info(file_complete)
        except urllib2.URLError:
            gscript.fatal("USGS download request has timed out. Network or formatting error.")
        except StandardError:
            cleanup_list.append(local_file)
            if LT_count:
                file_failed = "Download {0} of {1}: FAILED".format(
                            LT_count, TNM_count)
                gscript.fatal(file_failed)

    # sets already downloaded zip files or tiles to be extracted or imported
    if exist_file_list:
        for f in exist_file_list:
            if product_zip:
                LZ_paths.append(f)
            else:
                LT_paths.append(f)

    if product_zip == True:
        if tile_download_count == 0:
            pass
        else:
            gscript.message("Extracting data...")
        for z in LZ_paths:
            # Extract tiles from ZIP archives
            try:
                with zipfile.ZipFile(z, "r") as read_zip:
                    for f in read_zip.namelist():
                        if f.endswith(product_extension):
                            local_tile = os.path.join(work_dir, str(f))
                            if os.path.exists(local_tile):
                                os.remove(local_tile)
                            else:
                                read_zip.extract(f, work_dir)
                if os.path.exists(local_tile):
                    LT_count += 1
                    LT_paths.append(local_tile)
                    cleanup_list.append(local_tile)
            except:
                cleanup_list.append(local_tile)
                gscript.fatal("Unable to locate or extract IMG file from ZIP archive.")

    else:
        for t in LT_paths:
            LT_file_name = os.path.basename(t)
            LT_layer_name = os.path.splitext(LT_file_name)[0]
            patch_names.append(LT_layer_name)
            in_info = ("Importing and reprojecting {0}...").format(LT_file_name)
            gscript.info(in_info)
            # Workaround to not knowing resolution details for all extents
            if not product_resolution:
                try:
                    gscript.run_command('r.import', input=t, output=LT_layer_name,
                                    extent="region", resample=product_interpolation)
                    if not gui_k_flag:
                        cleanup_list.append(t)
                except CalledModuleError:
                    in_error = ("Unable to import '{0}'").format(LT_file_name)
                    gscript.fatal(in_error)
            # If extent resolution is known
            else:
                try:
                    gscript.run_command('r.import', input=t, output=LT_layer_name,
                                        resolution='value', resolution_value=product_resolution,
                                        extent="region", resample=product_interpolation)
                    if not gui_k_flag:
                        cleanup_list.append(t)
                except CalledModuleError:
                    in_error = ("Unable to import '{0}'").format(LT_file_name)
                    gscript.fatal(in_error)

    if LT_count > 1:
        try:
            gscript.use_temp_region()
            # set the resolution
            if product_resolution:
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
        print LT_count
        print tile_API_count
        gscript.fatal("Error downloading files. Please retry.")

    # Keep source files if 'k' flag active
    if gui_k_flag:
        src_msg = ("<k> flag selected: Source tiles remain in '{0}'").format(work_dir)
        gscript.info(src_msg)

    # set appropriate color table
    if gui_product == 'ned':
        gscript.run_command('r.colors', map=gui_output_layer, color='elevation')

def cleanup():
    # Remove files in cleanup_list
    for f in cleanup_list:
        if os.path.exists(f):
            gscript.try_remove(f)


if __name__ == "__main__":
    options, flags = gscript.parser()
    atexit.register(cleanup)
    sys.exit(main())
