#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 14 11:15:52 2017

@author: zechariah
"""

import sys
import osgeo.gdal
import grass.script as gscript

def main():
    # GET GRASS GIS g.region coordinates
    gscript.run_command('g.region', flags = 'p')

"""
VSI = "/vsizip/vsicurl/"
IMG_URL = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/IMG/n36w079.zip/"
IMG_NAME = "imgn36w079_13.img"
GDAL_READ = VSI + IMG_URL + IMG_NAME

INFO_OBJ = gdal.Info(GDAL_READ)
# Need to create info objects to use as input into gdal.translate call

IMG_DEST = "/home/zechariah/Downloads/GDAL_TEST/"
IMG_FULLPATH = IMG_DEST + IMG_NAME

gdal.Translate(IMG_FULLPATH, GDAL_READ, format='HFA')
# Add in g.region clipping boundaries
'''
Look into some sort of tiling mechanism that maybe joins multiple tiles
before applying clipping boundary, or figure out how to clip each subset
of a tile and use r.patch to join.
'''
"""

if __name__ == "__main__":
    sys.exit(main())