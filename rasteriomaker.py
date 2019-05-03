import numpy as np
import rasterio

land_polygons = rasterio.open("osm/land_polygons.geojson")