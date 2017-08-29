# GSoC2017-GRASS-GIS

DESCRIPTION
r.in.usgs downloads and patches select USGS datsasets to the current GRASS computational region and coordinate reference system. Associated parameters are automatically passed to The National Map Access API, downloaded to a user-specified local directory, then imported and patched through GRASS GIS.

AUTHOR
Zechariah Krautwurst, 2017 MGIST Candidate, North Carolina State University
(Google Summer of Code 2017, mentors: Anna Petrasova, Vaclav Petras)



Project Title:
GRASS GIS Locations from Public Data

Organization:
Google Summer of Code 2017
Open Source Geospatial Foundation (OSGeo)
GRASS GIS

Abstract:
r.in.usgs is an add-on module for GRASS GIS that greatly simplifies the process of downloading and using USGS raster datasets. 

Pre-GSoC:
Before r.in.usgs was created, USGS raster imagery was selected through a web-based interface, manually downloaded, and manually imported into GRASS GIS through a multi-step process. The process requires prior knowledge of USGS dataset parameters, spatial reference systems, coordinate reprojection, computational regions, and the appropriate GRASS GIS tools and methods.

Added value:
r.in.usgs provides a GRASS GIS GUI that suggests appropriate default parameters, as well as provides advanced options for downloading available USGS datasets. The module assembles user-input information with the required GRASS GIS parameters and tools to automatically download, import, reproject, and patch complex USGS raster data in a single process.

Continued Work:
r.in.usgs currently handles all three products from the USGS National Elevation Dataset (NED) as well as all three products from the National Land Cover Dataset (NLCD). Several other USGS datasets are made available for download but each requires custom formatting and further modifications to the r.in.usgs script processes.

Further development of the module should include continued incorporation of USGS datasets, as well as creating accessible tools for sources of international data. Ultimately, creating a module that allows GRASS GIS users to contribute to a centralized, automated repository of properly formatted publicly available datasets would provide a huge service to the open source GIS community.

r.in.usgs will be moved into the official GRASS GIS add-ons repository in the coming week.

Links and Documentation:
OSGeo project wiki:
https://trac.osgeo.org/grass/wiki/GSoC/2017/GRASSGISLocationsfromPublicData

Git repository:
https://github.com/zkwurst/GSoC2017-GRASS-GIS

Raw code:
https://raw.githubusercontent.com/zkwurst/GSoC2017-GRASS-GIS/master/r.in.usgs/r.in.usgs.py

Raw html documentation:
https://raw.githubusercontent.com/zkwurst/GSoC2017-GRASS-GIS/master/r.in.usgs/r.in.usgs.html

Google Docs version of html documentation:
https://docs.google.com/document/d/1jarl2X05A020_dv8YAcXjdPAONHrWpGnWigHWyzb3ys/edit#heading=h.gu5m0ou06qhs
