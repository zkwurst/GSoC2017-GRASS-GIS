# GSoC2017-GRASS-GIS

DESCRIPTION
r.in.usgs downloads and patches select USGS datsasets to the current GRASS computational region and coordinate reference system. Associated parameters are automatically passed to The National Map Access API, downloaded to a user-specified local directory, then imported and patched through GRASS GIS.

PARAMETERS

USGS Data Selection
'i' FLAG
If the 'i' flag is set, information about data meeting the input parameters is displayed without downloading the data.
If the 'i' flag is NOT set, the returned information will display and then begin immediate download.

USGS data product:
ned (National Elevation Dataset)
nlcd (National Land Cover Dataset)
NED (National Elevation Dataset)
NED data are available at resolutions of 1 arc-second (about 30 meters) and 1/3 arc-second (about 10 meters), and in limited areas at 1/9 arc-second (about 3 meters).

NED dataset:
1 arc-second
1/3 arc-second (about 10 meters)
1/9 arc-second (about 3 meters)(in limited areas)

NLCD (National Land Cover Dataset)
NLCD data are available for years 2001, 2006, and 2011. NLCD 2011 land cover was created on a path/row basis and mosaicked to create a seamless national product. The data in NLCD 2011 are completely integrated with NLCD 2001 and NLCD 2006. As part of the NLCD 2011 project, the NLCD 2001 and 2006 land cover data products were revised and reissued to provide full compatibility with the new NLCD 2011 products. NLCD 2011 land cover was developed for the conterminous United States and Alaska.

NLCD dataset:
NLCD 2001
NLCD 2006
NLCD 2011

NLCD subset:
Percent Developed Imperviousness
Percent Tree Canopy
Land Cover

Download Options

'k' FLAG
By default the 'k' flag is NOT set. Only files closest to the original source data are retained.
If the 'k' flag is set, extracted files from compressed archives are also kept within the download directory after GRASS import.

Directory for USGS data download and processing:
Specify a local directory that r.in.usgs will use to store and process USGS data

Name for output raster map:
Specify a name for the composite raster map that will be created by the module

Resampling method to use:
"default" will use a hardcoded resampling method selected for the USGS dataset.
NED default is 'bilinear'
NLCD default is 'nearest'

EXAMPLE
r.in.usgs example parameters:
r.in.usgs product=ned ned_dataset=1/3 arc-second output_directory=* output_name=*


Mapset g.region output is automatically detected:
g.region -p
projection: 3 (Latitude-Longitude)
zone:       0
datum:      nad83
ellipsoid:  grs80
north:      36:16:18.666609N
south:      35:17:53.333277N
west:       79:07:46.000246W
east:       78:08:02.333576W
nsres:      0:00:00.333333
ewres:      0:00:00.333333
rows:       10516
cols:       10751
cells:      113057516

Informational output:
USGS file(s) to download:
-------------------------
Total download size:    1.50 GB
Tile count:    4
USGS SRS:    wgs84
USGS tile titles:
USGS NED n36w079 1/3 arc-second 2013 1 x 1 degree IMG
USGS NED n37w079 1/3 arc-second 2013 1 x 1 degree IMG
USGS NED n36w080 1/3 arc-second 2013 1 x 1 degree IMG
USGS NED n37w080 1/3 arc-second 2013 1 x 1 degree IMG
-------------------------

REFERENCES
TNM Access API Guide 
(https://viewer.nationalmap.gov/help/documents/TNMAccessAPIDocumentation/TNMAccessAPIDocumentation.pdf)
National Elevation Dataset
(https://www.sciencebase.gov/catalog/item/4f70a58ce4b058caae3f8ddb)
National Land Cover Dataset
(https://catalog.data.gov/dataset/national-land-cover-database-nlcd-land-cover-collection)

SEE ALSO
g.region, r.import, r.patch, r.colors

AUTHOR
Zechariah Krautwurst, 2017 MGIST Candidate, North Carolina State University
(Google Summer of Code 2017, mentors: Anna Petrasova, Vaclav Petras)


