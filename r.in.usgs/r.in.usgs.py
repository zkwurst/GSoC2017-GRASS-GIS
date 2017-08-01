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
#% options: vectorcmb, nhd, nbdmi, gnis, nsd, ned, naip, ustopo, woodland, hro, nlcd, smallscale, histtopo, nedsrc, ntd, nbd
#% answer: ned
#% label: USGS data product
#% description: Choose which available USGS data product to query
#% guisection: USGS Data Selection
#%end

#%option
#% key: dataset
#% required: yes
#% options: NHDPlus High Resolution (NHDPlus HR) Beta, National Hydrography Dataset (NHD), Watershed Boundary Dataset (WBD), 5 meter DEM (Alaska only), 2 arc-second DEM - Alaska, 1/3 arc-second DEM, 1 meter DEM, 1/9 arc-second DEM, Contours (1:24,000-scale), 1 arc-second DEM, US Topo Current, US Topo Non-Current, National Land Cover Database (NLCD) - 2006, National Land Cover Database (NLCD) - 2011, National Land Cover Database (NLCD) - 2001, Hydrography (Small-scale), Contours (Small-scale), Transportation (Small-scale), Elevation (Small-scale), Land Cover (Small-scale), Orthoimagery (Small-scale), Structures (Small-scale), Boundaries (Small-scale), Lidar Point Cloud (LPC), DEM Source (OPR), Ifsar Orthorectified Radar Image (ORI), Ifsar Digital Surface Model (DSM), USFS Roads, National Transportation Dataset
#% answer: ned
#% label: USGS dataset
#% description: Choose which available USGS dataset to query
#% guisection: USGS Data Selection
#%end


#%option
#% key: extent
#% required: yes
#% options: HU-4 Subregion, State, HU-8 Subbasin, National, HU-2 Region, Varies, 1 x 1 degree, 10000 x 10000 meter, 15 x 15 minute, 7.5 x 7.5 minute, 3 x 3 degree, North America, Contiguous US
#% label: USGS dataset extent
#% description: Choose which available USGS dataset extent
#% guisection: USGS Data Selection
#%end

#%option
#% key: other
#% required: no
#% options: Percent Developed Imperviousness, Percent Tree Canopy, Land Cover
#% label: extra options
#% description: Options specific to product subsets
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

def main():
    # Set GRASS GUI options and flags to python variables
    gui_product = options['product']
    gui_dataset = options['dataset']
    gui_extent = options['extent']
    gui_other = options['other']
    gui_output_layer = options['output']
    gui_resampling_method = options['resampling_method']
    gui_i_flag = flags['i']
    global gui_k_flag
    gui_k_flag = flags['k']
    work_dir = options['output_directory']

    # Data dictionary generator

    dict_TNM_API_URL = "https://viewer.nationalmap.gov/tnmaccess/api/datasets?"
    dict_TNM_API_GET = urllib2.urlopen(dict_TNM_API_URL, timeout=12)
    dict_returnJSON = json.load(dict_TNM_API_GET)
    
    dict_TNM_API_URL = "https://viewer.nationalmap.gov/tnmaccess/api/datasets?"
    dict_TNM_API_GET = urllib2.urlopen(dict_TNM_API_URL, timeout=12)
    dict_returnJSON = json.load(dict_TNM_API_GET)

    usgs_dict = {}
    for product in dict_returnJSON:
        prod_title = str(product["sbDatasetTag"])
        prod_id = str(product["internalId"])
        prod_tags = product['tags']
        usgs_dict[prod_id] = {}
        usgs_dict[prod_id]["product"] = {}
        usgs_dict[prod_id] = {"product":prod_title}
        usgs_dict[prod_id]["dataset"] = {}
        for tag in prod_tags:
            usgs_dict[prod_id]["dataset"][tag] = {}
            prod_extents = prod_tags[tag]["extentsFormats"]
            usgs_dict[prod_id]["dataset"][tag]["extents"] = {}
            prod_data_tag = prod_tags[tag]["sbDatasetTag"]
            usgs_dict[prod_id]["dataset"][tag]["sbDatasetTag"] = prod_data_tag
            for prod_extent in prod_extents:
                usgs_dict[prod_id]["dataset"][tag]["extents"][prod_extent] = {}
                prod_formats = prod_tags[tag]["extentsFormats"][str(prod_extent)]
                usgs_dict[prod_id]["dataset"][tag]["extents"][prod_extent]["formats"] = []
                usgs_dict[prod_id]["dataset"][tag]["extents"][prod_extent]["formats"] = prod_formats

    usgs_product_dict = {}
    for p in usgs_dict:
        product_title = usgs_dict[p]['product']
        product_datasets = []
        product_extents = []
        product_formats = []
        first_formats = ['IMG', 'GeoTIFF', 'GeoPDF']
        second_formats = ['TIFF']
        third_formats = ['Shapefile']
        product_format = None
        for ds in usgs_dict[p]['dataset']:
            product_datasets.append(str(ds))
            for e in usgs_dict[p]['dataset'][ds]['extents']:
                if e not in product_extents:
                    product_extents.append(str(e))
                for f in usgs_dict[p]['dataset'][ds]['extents'][e]['formats']:
                    if f not in product_formats:
                        product_formats.append(str(f))
                    if f in first_formats:
                        product_format = f
                    else:
                        if f in second_formats:
                            product_format = f
                        else:
                            if f in third_formats:
                                product_format = f
                        
        usgs_product_dict[p] = {
             'product':product_title,
             'dataset':product_datasets,
             'extent':product_extents,
             'format':product_format,
             'srs':'wgs84',
             'srs_proj4':"+proj=longlat +ellps=GRS80 +datum=NAD83 +nodefs",
             'interpolation':None}
        if p == 'ned':
            usgs_product_dict[p]['dataset'] = {
                    "1 arc-second DEM": (1. / 3600, 30, 100),
                    "1/3 arc-second DEM": (1. / 3600 / 3, 10, 30),
                    "1/9 arc-second DEM": (1. / 3600 / 9, 3, 10)}
            usgs_product_dict[p]['interpolation'] = 'bilinear'


    # Dynamic variables called from USGS data dict
    nav_string = usgs_product_dict[gui_product]
    product_title = nav_string['product']
    product_format = nav_string['format']
    product_dataset = nav_string['dataset']
    product_tag = usgs_dict[gui_product]['dataset'][gui_dataset]['sbDatasetTag']
    product_srs = usgs_product_dict[gui_product]['srs']
    product_proj4 = nav_string['srs_proj4']
    product_interpolation = nav_string['interpolation']
    
    # current units
    try:
        proj = gscript.parse_command('g.proj', flags='g')
        if gscript.locn_is_latlong():
            product_resolution = product_dataset[gui_dataset][0]
        elif float(proj['meters']) == 1:
            product_resolution = product_dataset[gui_dataset][1]
        else:
            # we assume feet
            product_resolution = product_dataset[gui_dataset][2]
        
        print "Product Resolution = " + str(product_resolution)
    except TypeError:
        product_resolution = False

    if gui_resampling_method == 'default':
        gui_resampling_method = nav_string['interpolation']
        gscript.verbose(_("The default resampling method for product {product} is {res}").format(product=gui_product,
                        res=usgs_product_dict[p]['interpolation']))

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
    
#    gui_prod_str = product_title + " " + gui_extent
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
                if abs(existing_LZ_size - TNM_tile_size) > size_diff_tolerance:
                    cleanup_list.append(pre_local_zip)
                    down_list()
                else:
                    exist_zip_list.append(pre_local_zip)
            if gui_other:
                if gui_other in TNM_title:
                    down_list()
                else:
                    pass
            else:
                down_list()
        tile_needed_count = len(dwnld_url)
        exist_zip_count = len(exist_zip_list)
        tile_download_count = tile_needed_count - exist_zip_count
    elif tile_API_count == 0:
        gscript.fatal("Zero tiles available for given input parameters.")

    if exist_zip_list:
        exist_msg = "\n{0} ZIP archive(s) exist locally and will be used by module.".format(len(exist_zip_list))
        gscript.message(exist_msg)
    if cleanup_list:
        cleanup_msg = "\n{0} existing incomplete ZIP archive(s) detected and removed. Run module again.".format(len(cleanup_list))
        gscript.fatal(cleanup_msg)
    
    if dwnld_size:
        total_size = sum(dwnld_size)
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
    LZ_count = 0
    LT_count = 0
    global LT_paths
    LT_paths = []
    LZ_paths = []
    patch_names = []

    # Download ZIP files
    for url in dwnld_url:
        zip_name = url.split('/')[-1]
        local_zip = os.path.join(work_dir, zip_name)
        try:
            dwnld_req = urllib2.urlopen(url, timeout=12)
            download_bytes = int(dwnld_req.info()['Content-Length'])
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
            LZ_count += 1
            LZ_paths.append(local_zip)
            zip_complete = "Download {0} of {1}: COMPLETE".format(
                    LZ_count, TNM_count)
            gscript.info(zip_complete)
        except urllib2.URLError:
            gscript.fatal("USGS download request has timed out. Network or formatting error.")
        except StandardError:
            cleanup_list.append(local_zip)
            zip_failed = "Download {0} of {1}: FAILED".format(
                        LZ_count, TNM_count)
            gscript.fatal(zip_failed)

    # adds already downloaded zip file paths 
    if exist_zip_list:
        for z in exist_zip_list:
            LZ_paths.append(z)
    
    if tile_download_count == 0:
        pass
    else:
        gscript.message("Extracting data...")


    extensions_dict = {
            "IMG":".img",
            "GeoTIFF":".tif",
            "GeoPDF":".pdf",
            "TIFF":".tif",
            "Shapefile":".shp"
            }
    product_file_ext = extensions_dict[product_format]
    

    for z in LZ_paths:
        # Extract tiles from ZIP archives
        try:
            with zipfile.ZipFile(z, "r") as read_zip:
                for f in read_zip.namelist():
                    if f.endswith(product_file_ext):
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
                                extent="region", resample=gui_resampling_method)
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
