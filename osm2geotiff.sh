rm -rf osm
mkdir osm
ADDRESS="Macquarie University"
CLEAN_ADDRESS=$(echo $ADDRESS | sed -E --expression='s/[^A-Za-z0-9]+/_/g')
rm -rf data/osm${CLEAN_ADDRESS}.tif
osmxtract --address "${ADDRESS}" --buffer 10000 \
           --tag land_polygons --geom polygon osm/land_polygons.geojson



osmxtract --address "${ADDRESS}" --buffer 10000 \
           --tag building --geom polygon osm/buildings.geojson

osmxtract --address "${ADDRESS}" --buffer 10000 \
           --tag highway \
           --values "primary,secondary,tertiary" \
          --case-insensitive --geom linestring \
            osm/major_roads.geojson

osmxtract --address "${ADDRESS}" --buffer 10000 \
           --tag natural --geom polygon \
            osm/natural.geojson                   

ogr2ogr  osm/land_polygons.shp osm/land_polygons.geojson
ogr2ogr  osm/buildings.shp osm/buildings.geojson
ogr2ogr  osm/major_roads.shp osm/major_roads.geojson
ogr2ogr  osm/natural.shp osm/natural.geojson


gdal_rasterize -burn 255 -of gtiff -ts 10 10 osm/land_polygons.shp data/osm${CLEAN_ADDRESS}.tif