#!/usr/bin/env python3
"""
export_qgis_project.py

Generates a fully configured, standards-compliant QGIS 3.x project file (heritage_survey.qgs)
and embeds it directly inside the GeoPackage (qgis_projects table).

Key Features (v0.2):
- Native OGR provider tags resolving the "missing layer" error in desktop QGIS and QField
- GDA2020 CRS support (EPSG:7844 Geographic or MGA2020 Zones 49-56, EPSG:7849-7856)
- Grouped layer hierarchy (Boundaries, Landscape Features, Trees & Scars, Artefacts, Basemaps)
- Web OpenTopoMap and OpenStreetMap XYZ raster tile layers
- Color-coded symbology with clear cartographic contrast
- 1:N QGIS Relations (Mound/Features -> Boundary Polygons & Lines, Trees -> Scars, Features -> Media)
- Field editor widgets with ValueMap combobox dropdowns from 111 controlled vocabularies
- Default values for author ('Mick Morrison') and timestamp (now())
- Relative path configuration for seamless offline multi-device transfer (Topcon FC-6000 & iPads)
"""

import os
import sys
import json
import sqlite3
import argparse
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR = os.path.join(SCRIPT_DIR, 'schema')
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
GPKG_PATH = os.path.join(DATA_DIR, 'heritage_survey.gpkg')
QGS_PATH = os.path.join(DATA_DIR, 'heritage_survey.qgs')

# GDA2020 CRS Definitions
def get_crs_xml_snippet(epsg_code):
    if epsg_code == 7844:
        return """<spatialrefsys>
        <wkt>GEOGCRS["GDA2020",DATUM["Geocentric Datum of Australia 2020",ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],CS[ellipsoidal,2],AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],USAGE[SCOPE["Geodesy, cadastre, engineering survey, topographic mapping."],AREA["Australia."],BBOX[-60.55,93.41,-8.47,173.34]],ID["EPSG",7844]]</wkt>
        <proj4>+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs</proj4>
        <srsid>7844</srsid>
        <srid>7844</srid>
        <authid>EPSG:7844</authid>
        <description>GDA2020</description>
        <projectionacronym>longlat</projectionacronym>
        <ellipsoidacronym>EPSG:7019</ellipsoidacronym>
        <geographicflag>true</geographicflag>
      </spatialrefsys>"""
    elif 7849 <= epsg_code <= 7856:
        zone = epsg_code - 7800
        cm = zone * 6 - 183
        return f"""<spatialrefsys>
        <wkt>PROJCRS["GDA2020 / MGA zone {zone}",BASEGEOGCRS["GDA2020",DATUM["Geocentric Datum of Australia 2020",ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",7844]],CONVERSION["Map Grid of Australia zone {zone}",METHOD["Transverse Mercator",ID["EPSG",9807]],PARAMETER["Latitude of natural origin",0,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",{cm},ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.9996,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",10000000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["(E)",east,ORDER[1],LENGTHUNIT["metre",1]],AXIS["(N)",north,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Engineering survey, topographic mapping."],AREA["Australia."],BBOX[-45,110,-10,155]],ID["EPSG",{epsg_code}]]</wkt>
        <proj4>+proj=utm +zone={zone} +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs</proj4>
        <srsid>{epsg_code}</srsid>
        <srid>{epsg_code}</srid>
        <authid>EPSG:{epsg_code}</authid>
        <description>GDA2020 / MGA zone {zone}</description>
        <projectionacronym>utm</projectionacronym>
        <ellipsoidacronym>EPSG:7019</ellipsoidacronym>
        <geographicflag>false</geographicflag>
      </spatialrefsys>"""
    else:
        # Default fallback EPSG:7854 (Zone 54)
        return get_crs_xml_snippet(7854)

# Web Tile CRS Snippet (EPSG:3857)
WEB_MERCATOR_CRS = """<spatialrefsys>
        <wkt>PROJCRS["WGS 84 / Pseudo-Mercator",BASEGEOGCRS["WGS 84",DATUM["WGS_1984",ELLIPSOID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],CONVERSION["Popular Visualisation Pseudo-Mercator",METHOD["Popular Visualisation Pseudo Mercator",ID["EPSG",1024]],PARAMETER["Latitude of natural origin",0,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",0,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["False easting",0,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",0,LENGTHUNIT["metre",1],ID["EPSG",8807]],CS[Cartesian,2],AXIS["easting (X)",east,ORDER[1],LENGTHUNIT["metre",1]],AXIS["northing (Y)",north,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Web mapping and visualisation."],AREA["World between 85.06 S and 85.06 N."],BBOX[-85.06,-180,85.06,180]],ID["EPSG",3857]]</wkt>
        <proj4>+proj=merc +a=6378137 +b=6378137 +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +wktext +no_defs</proj4>
        <srsid>3857</srsid>
        <srid>3857</srid>
        <authid>EPSG:3857</authid>
        <description>WGS 84 / Pseudo-Mercator</description>
        <projectionacronym>merc</projectionacronym>
        <ellipsoidacronym>EPSG:7030</ellipsoidacronym>
        <geographicflag>false</geographicflag>
      </spatialrefsys>"""

def clean_col_name(name):
    cleaned = name.strip().replace('--', '_').replace('-', '_').replace(' ', '_').replace('(', '').replace(')', '')
    cleaned = cleaned.replace('/', '_').replace('.', '').replace(',', '')
    while '__' in cleaned:
        cleaned = cleaned.replace('__', '_')
    return cleaned.lower().strip('_')

def build_field_configuration_xml(table_name, schema_fields, vocabularies, zone):
    """Builds QGIS field edit widgets, default values, and ValueMap dropdowns"""
    configs = []
    default_vals = []
    
    # 1. Author field default
    configs.append("""      <field name="author">
        <editWidget type="TextEdit">
          <config>
            <Option type="Map">
              <Option type="bool" name="IsMultiline" value="false"/>
              <Option type="bool" name="UseHtml" value="false"/>
            </Option>
          </config>
        </editWidget>
      </field>""")
    default_vals.append("""      <default field="author" expression="'Mick Morrison'" applyOnUpdate="0"/>""")

    # 2. Timestamp default
    configs.append("""      <field name="timestamp">
        <editWidget type="DateTime">
          <config>
            <Option type="Map">
              <Option type="bool" name="allow_null" value="false"/>
              <Option type="bool" name="calendar_popup" value="true"/>
              <Option type="QString" name="display_format" value="yyyy-MM-dd HH:mm:ss"/>
              <Option type="QString" name="field_format" value="yyyy-MM-dd HH:mm:ss"/>
            </Option>
          </config>
        </editWidget>
      </field>""")
    default_vals.append("""      <default field="timestamp" expression="now()" applyOnUpdate="0"/>""")

    # 3. MGA Zone default if present
    configs.append("""      <field name="mga_zone">
        <editWidget type="Range">
          <config>
            <Option type="Map">
              <Option type="bool" name="AllowNull" value="true"/>
              <Option type="int" name="Max" value="56"/>
              <Option type="int" name="Min" value="49"/>
              <Option type="int" name="Step" value="1"/>
            </Option>
          </config>
        </editWidget>
      </field>""")
    default_vals.append(f"""      <default field="mga_zone" expression="{zone if zone else 54}" applyOnUpdate="0"/>""")

    # 4. Vocab fields
    for f in schema_fields:
        v_ref = f.get('vocab_ref')
        if not v_ref or v_ref not in vocabularies:
            continue
        col_name = clean_col_name(f['name'])
        vdata = vocabularies[v_ref]
        opts = vdata.get('options', [])
        if not opts:
            continue
            
        opt_entries = []
        for opt in opts:
            val = opt['value'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            opt_entries.append(f"""              <Option type="Map"><Option type="QString" name="{val}" value="{val}"/></Option>""")
        
        map_content = "\n".join(opt_entries)
        field_xml = f"""      <field name="{col_name}">
        <editWidget type="ValueMap">
          <config>
            <Option type="Map">
              <Option type="List" name="map">
{map_content}
              </Option>
            </Option>
          </config>
        </editWidget>
      </field>"""
        configs.append(field_xml)

    joined_configs = "\n".join(configs)
    joined_defaults = "\n".join(default_vals)
    return f"""    <fieldConfiguration>
{joined_configs}
    </fieldConfiguration>
    <defaults>
{joined_defaults}
    </defaults>"""

def build_vector_layer_xml(lid, layer_name, table_name, geom_type, crs_snippet, color, outline_color, size_or_width, schema_fields, vocabularies, zone):
    is_poly = (geom_type == 'Polygon')
    is_line = (geom_type == 'LineString')
    is_point = (geom_type == 'Point')
    
    if is_poly:
        sym_type = 'fill'
        symbol_xml = f"""      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="0.45" clip_to_extent="1">
            <layer class="SimpleFill" locked="0" pass="0">
              <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="color" v="{color}"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="offset" v="0,0"/>
              <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="offset_unit" v="MM"/>
              <prop k="outline_color" v="{outline_color}"/>
              <prop k="outline_style" v="solid"/>
              <prop k="outline_width" v="{size_or_width}"/>
              <prop k="outline_width_unit" v="MM"/>
              <prop k="style" v="solid"/>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>"""
    elif is_line:
        sym_type = 'line'
        symbol_xml = f"""      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="line" name="0" alpha="1" clip_to_extent="1">
            <layer class="SimpleLine" locked="0" pass="0">
              <prop k="align_dash_pattern" v="0"/>
              <prop k="capstyle" v="square"/>
              <prop k="customdash" v="5;2"/>
              <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="customdash_unit" v="MM"/>
              <prop k="dash_pattern_offset" v="0"/>
              <prop k="dash_pattern_offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="dash_pattern_offset_unit" v="MM"/>
              <prop k="draw_inside_polygon" v="0"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="line_color" v="{color}"/>
              <prop k="line_style" v="dash"/>
              <prop k="line_width" v="{size_or_width}"/>
              <prop k="line_width_unit" v="MM"/>
              <prop k="offset" v="0"/>
              <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="offset_unit" v="MM"/>
              <prop k="ring_filter" v="0"/>
              <prop k="trim_distance_end" v="0"/>
              <prop k="trim_distance_end_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="trim_distance_end_unit" v="MM"/>
              <prop k="trim_distance_start" v="0"/>
              <prop k="trim_distance_start_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="trim_distance_start_unit" v="MM"/>
              <prop k="tweak_dash_pattern_on_corners" v="0"/>
              <prop k="use_custom_dash" v="0"/>
              <prop k="width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>"""
    else:
        # Point marker
        shape = 'circle'
        if 'shelter' in table_name or 'glass' in table_name or 'metal' in table_name:
            shape = 'diamond'
        elif 'hearth' in table_name or 'exposure' in table_name or 'historical' in table_name or 'ceramic' in table_name:
            shape = 'square'
        elif 'scars' in table_name or 'weapons' in table_name:
            shape = 'triangle'
        elif 'burial' in table_name:
            shape = 'cross'
        elif 'point_of_interest' in table_name:
            shape = 'star'

        symbol_xml = f"""      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="marker" name="0" alpha="0.9" clip_to_extent="1">
            <layer class="SimpleMarker" locked="0" pass="0">
              <prop k="angle" v="0"/>
              <prop k="color" v="{color}"/>
              <prop k="horizontal_anchor_point" v="1"/>
              <prop k="joinstyle" v="bevel"/>
              <prop k="name" v="{shape}"/>
              <prop k="offset" v="0,0"/>
              <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="offset_unit" v="MM"/>
              <prop k="outline_color" v="{outline_color}"/>
              <prop k="outline_style" v="solid"/>
              <prop k="outline_width" v="0.4"/>
              <prop k="outline_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="outline_width_unit" v="MM"/>
              <prop k="scale_method" v="diameter"/>
              <prop k="size" v="{size_or_width}"/>
              <prop k="size_map_unit_scale" v="3x:0,0,0,0,0,0"/>
              <prop k="size_unit" v="MM"/>
              <prop k="vertical_anchor_point" v="1"/>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>"""

    field_conf = build_field_configuration_xml(table_name, schema_fields, vocabularies, zone)

    return f"""    <maplayer type="vector" id="{lid}" name="{layer_name}" geometry="{geom_type}" minScale="1e+08" maxScale="0" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" hasScaleBasedVisibilityFlag="0" styleCategories="AllStyleCategories" autoRefreshEnabled="0">
      <id>{lid}</id>
      <datasource>./heritage_survey.gpkg|layername={table_name}</datasource>
      <keywordList>
        <value></value>
      </keywordList>
      <layername>{layer_name}</layername>
      <srs>
        {crs_snippet}
      </srs>
      <resourceMetadata>
        <identifier></identifier>
        <parentidentifier></parentidentifier>
        <type>dataset</type>
        <title>{layer_name}</title>
        <abstract></abstract>
      </resourceMetadata>
      <provider encoding="UTF-8">ogr</provider>
      <vectorjoins/>
      <layerDependencies/>
      <dataDependencies/>
      <expressionfields/>
      <map-layer-style-manager current="default">
        <map-layer-style name="default"/>
      </map-layer-style-manager>
      <auxiliaryLayer/>
      <flags>
        <Identifiable>1</Identifiable>
        <Removable>1</Removable>
        <Searchable>1</Searchable>
        <Private>0</Private>
      </flags>
{symbol_xml}
      <blendMode>0</blendMode>
      <featureBlendMode>0</featureBlendMode>
      <layerOpacity>1</layerOpacity>
{field_conf}
    </maplayer>"""

def build_xyz_tile_layer_xml(lid, name, url, zmax):
    encoded_url = url.replace('{', '%7B').replace('}', '%7D')
    return f"""    <maplayer type="raster" id="{lid}" name="{name}" autoRefreshTime="0" autoRefreshMode="Disabled" hasScaleBasedVisibilityFlag="0" minScale="1e+08" maxScale="0" styleCategories="AllStyleCategories" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="">
      <id>{lid}</id>
      <datasource>type=xyz&amp;url={encoded_url}&amp;zmax={zmax}&amp;zmin=0</datasource>
      <keywordList>
        <value></value>
      </keywordList>
      <layername>{name}</layername>
      <srs>
        {WEB_MERCATOR_CRS}
      </srs>
      <resourceMetadata>
        <identifier></identifier>
        <parentidentifier></parentidentifier>
        <type>dataset</type>
        <title>{name}</title>
        <abstract></abstract>
      </resourceMetadata>
      <provider>wms</provider>
      <noData>
        <noDataList bandNo="1" useSrcNoData="0"/>
      </noData>
      <map-layer-style-manager current="default">
        <map-layer-style name="default"/>
      </map-layer-style-manager>
      <flags>
        <Identifiable>1</Identifiable>
        <Removable>1</Removable>
        <Searchable>1</Searchable>
        <Private>0</Private>
      </flags>
      <pipe-data>
        <rasterrenderer type="singlebandcolordata" opacity="1" alphaBand="-1" band="1">
          <rasterTransparency/>
          <minMaxOrigin>
            <limits>None</limits>
            <extent>WholeRaster</extent>
            <statAccuracy>Estimated</statAccuracy>
            <cumulativeCutLower>0.02</cumulativeCutLower>
            <cumulativeCutUpper>0.98</cumulativeCutUpper>
            <stdDevFactor>2</stdDevFactor>
          </minMaxOrigin>
        </rasterrenderer>
        <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
        <huesaturation colorizeGreen="128" colorizeStrength="100" colorizeOn="0" saturation="0" invertColors="0" colorizeRed="255" colorizeBlue="128"/>
        <rasterresampler maxOversampling="2"/>
        <resamplingStage>resamplingFilter</resamplingStage>
      </pipe-data>
      <blendMode>0</blendMode>
    </maplayer>"""

def export_project(target_crs_id=7854, zone=54):
    """Main project builder called directly or from generate_geopackage.py"""
    print(f"Configuring QGIS project with target CRS EPSG:{target_crs_id}...")

    schema_path = os.path.join(SCHEMA_DIR, 'faims_extracted_schema.json')
    vocab_path = os.path.join(SCHEMA_DIR, 'vocabularies.json')

    schema = {}
    vocabularies = {}
    if os.path.exists(schema_path):
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    if os.path.exists(vocab_path):
        with open(vocab_path, 'r', encoding='utf-8') as f:
            vocabularies = json.load(f)

    # Helper to get schema fields for an entity
    def get_entity_fields(ent_key):
        ent = schema.get('entities', {}).get(ent_key, {})
        fields = []
        for tab_fields in ent.get('tabs', {}).values():
            fields.extend(tab_fields)
        return fields

    crs_snippet = get_crs_xml_snippet(target_crs_id)

    # 1. Landscape Boundaries & Extents
    boundary_layers = [
        ('feature_boundaries_layer', 'Feature Boundary Polygons', 'feature_boundaries', 'Polygon', '#2b83ba', '#1c5275', 0.8, []),
        ('feature_lines_layer', 'Feature Line Extents', 'feature_lines', 'LineString', '#e66101', '#e66101', 0.8, [])
    ]

    # 2. Landscape Features (Sites, Mounds, Shelters, Burials, POIs)
    landscape_features = [
        ('mound_layer', 'Mounds', 'mound', 'Point', '#8c510a', '#000000', 4.8, get_entity_fields('Mound')),
        ('surface_exposure_layer', 'Surface Exposures', 'surface_exposure', 'Point', '#d8b365', '#000000', 4.2, get_entity_fields('Surface_Exposure')),
        ('rock_shelter_layer', 'Rock Shelters', 'rock_shelter', 'Point', '#543005', '#000000', 4.5, get_entity_fields('Rock_Shelter')),
        ('discrete_hearth_artefact_layer', 'Hearths', 'discrete_hearth_artefact', 'Point', '#e66101', '#000000', 4.2, get_entity_fields('Discrete_Hearth_Artefact')),
        ('burial_layer', 'Burials', 'burial', 'Point', '#762a83', '#000000', 4.8, get_entity_fields('Burial')),
        ('point_of_interest_layer', 'Points of Interest', 'point_of_interest', 'Point', '#fdae61', '#000000', 4.5, get_entity_fields('Point_of_Interest'))
    ]

    # 3. Trees & Scars
    tree_layers = [
        ('tree_layer', 'Historic / Scarred Trees', 'tree', 'Point', '#276419', '#000000', 4.5, get_entity_fields('Tree')),
        ('tree_scars_layer', 'Tree Scars (Child)', 'tree_scars', 'Point', '#7fbc41', '#000000', 3.6, get_entity_fields('Scar'))
    ]

    # 4. Artefact Recordings
    artefact_layers = [
        ('flaked_stone_artefact_layer', 'Flaked Stone Artefacts', 'flaked_stone_artefact', 'Point', '#2b83ba', '#000000', 3.8, get_entity_fields('Flaked_Stone_Artefact')),
        ('other_stone_artefact_layer', 'Other Stone Artefacts', 'other_stone_artefact', 'Point', '#5e3c99', '#000000', 3.8, get_entity_fields('Other_Stone_Artefact')),
        ('knapped_glass_artefact_layer', 'Knapped Glass Artefacts', 'knapped_glass_artefact', 'Point', '#80cdc1', '#000000', 3.8, get_entity_fields('Knapped_Glass_Artefact')),
        ('glass_artefact_layer', 'Glass Artefacts', 'glass_artefact', 'Point', '#018571', '#000000', 3.8, get_entity_fields('Glass_Artefact')),
        ('ceramic_artefact_layer', 'Ceramic Artefacts', 'ceramic_artefact', 'Point', '#df65b0', '#000000', 3.8, get_entity_fields('Ceramic_Artefact')),
        ('buttons_layer', 'Buttons', 'buttons', 'Point', '#dfc27d', '#000000', 3.2, get_entity_fields('Buttons')),
        ('metal_artefact_layer', 'Metal Artefacts', 'metal_artefact', 'Point', '#a6611a', '#000000', 3.8, get_entity_fields('Metal_Artefact')),
        ('weapons_and_ammunition_layer', 'Weapons &amp; Ammunition', 'weapons_and_ammunition', 'Point', '#404040', '#000000', 4.0, get_entity_fields('Weapons_and_Ammunition')),
        ('historical_feature_layer', 'Historical Features', 'historical_feature', 'Point', '#c51b7d', '#000000', 4.0, get_entity_fields('Historical_Feature')),
        ('misc_artefact_layer', 'Miscellaneous Artefacts', 'misc_artefact', 'Point', '#999999', '#000000', 3.5, get_entity_fields('Misc_Artefact'))
    ]

    all_vector_groups = [
        ("Boundaries &amp; Linear Extents", boundary_layers),
        ("Landscape Features", landscape_features),
        ("Trees &amp; Cultural Scars", tree_layers),
        ("Artefact Recordings", artefact_layers)
    ]

    map_layers_xml = []
    layer_tree_groups_xml = []

    for group_name, group_layers in all_vector_groups:
        tree_children = []
        for lid, lname, tbl, gtype, col, outcol, size, flds in group_layers:
            layer_xml = build_vector_layer_xml(lid, lname, tbl, gtype, crs_snippet, col, outcol, size, flds, vocabularies, zone)
            map_layers_xml.append(layer_xml)
            tree_children.append(f"""      <layer-tree-layer id="{lid}" name="{lname}" checked="Qt::Checked" expanded="1"/>""")
        
        children_str = "\n".join(tree_children)
        layer_tree_groups_xml.append(f"""    <layer-tree-group name="{group_name}" checked="Qt::Checked" expanded="1">
{children_str}
    </layer-tree-group>""")

    # Basemap layers
    map_layers_xml.append(build_xyz_tile_layer_xml('opentopo_layer', 'OpenTopoMap', 'https://tile.opentopomap.org/{z}/{x}/{y}.png', 17))
    map_layers_xml.append(build_xyz_tile_layer_xml('osm_layer', 'OpenStreetMap', 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', 19))

    layer_tree_groups_xml.append("""    <layer-tree-group name="Basemaps (Online / Cached)" checked="Qt::Checked" expanded="1">
      <layer-tree-layer id="opentopo_layer" name="OpenTopoMap" checked="Qt::Checked" expanded="0"/>
      <layer-tree-layer id="osm_layer" name="OpenStreetMap" checked="Qt::Unchecked" expanded="0"/>
    </layer-tree-group>""")

    # QGIS Relations XML (1:N relationships for child entities and boundaries)
    relations_xml = """    <relations>
      <relation id="rel_mound_boundaries" name="Mound Boundaries" strength="Composition">
        <referencedLayer id="mound_layer"/>
        <referencingLayer id="feature_boundaries_layer"/>
        <fieldPair referenced="record_id" referencing="parent_feature_id"/>
      </relation>
      <relation id="rel_surface_exposure_boundaries" name="Surface Exposure Boundaries" strength="Composition">
        <referencedLayer id="surface_exposure_layer"/>
        <referencingLayer id="feature_boundaries_layer"/>
        <fieldPair referenced="record_id" referencing="parent_feature_id"/>
      </relation>
      <relation id="rel_rock_shelter_boundaries" name="Rock Shelter Boundaries" strength="Composition">
        <referencedLayer id="rock_shelter_layer"/>
        <referencingLayer id="feature_boundaries_layer"/>
        <fieldPair referenced="record_id" referencing="parent_feature_id"/>
      </relation>
      <relation id="rel_historical_feature_boundaries" name="Historical Feature Boundaries" strength="Composition">
        <referencedLayer id="historical_feature_layer"/>
        <referencingLayer id="feature_boundaries_layer"/>
        <fieldPair referenced="record_id" referencing="parent_feature_id"/>
      </relation>
      <relation id="rel_mound_lines" name="Mound Linear Features" strength="Composition">
        <referencedLayer id="mound_layer"/>
        <referencingLayer id="feature_lines_layer"/>
        <fieldPair referenced="record_id" referencing="parent_feature_id"/>
      </relation>
      <relation id="rel_tree_scars" name="Tree Scars" strength="Composition">
        <referencedLayer id="tree_layer"/>
        <referencingLayer id="tree_scars_layer"/>
        <fieldPair referenced="record_id" referencing="parent_tree_id"/>
      </relation>
    </relations>"""

    joined_layer_tree = "\n".join(layer_tree_groups_xml)
    joined_map_layers = "\n".join(map_layers_xml)

    qgs_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="Australian Heritage Landscape Survey &amp; Artefact Recording" version="3.28.0">
  <homePath path=""/>
  <title>Australian Heritage Landscape Survey &amp; Artefact Recording</title>
  <autotransaction active="0"/>
  <evaluateDefaultValues active="1"/>
  <trust active="0"/>
  <projectCrs>
    {crs_snippet}
  </projectCrs>
  <layer-tree-group>
    <customproperties>
      <Option/>
    </customproperties>
{joined_layer_tree}
    <customproperties>
      <Option/>
    </customproperties>
  </layer-tree-group>
  <snapping-settings enabled="1" mode="2" intersection-snapping="1" type="1" tolerance="12" unit="1" minScale="0" maxScale="0" scaleDependencyMode="0">
    <individual-layer-settings>
      <layer-setting id="feature_boundaries_layer" enabled="1" type="1" tolerance="12" units="1" minScale="0" maxScale="0"/>
      <layer-setting id="feature_lines_layer" enabled="1" type="1" tolerance="12" units="1" minScale="0" maxScale="0"/>
      <layer-setting id="mound_layer" enabled="1" type="1" tolerance="12" units="1" minScale="0" maxScale="0"/>
    </individual-layer-settings>
  </snapping-settings>
  <projectlayers>
{joined_map_layers}
  </projectlayers>
  <properties>
    <Paths>
      <Absolute type="bool">false</Absolute>
    </Paths>
    <SpatialRefSys>
      <ProjectionsEnabled type="int">1</ProjectionsEnabled>
    </SpatialRefSys>
    <Gui>
      <SelectionColorRedPart type="int">255</SelectionColorRedPart>
      <SelectionColorGreenPart type="int">255</SelectionColorGreenPart>
      <SelectionColorBluePart type="int">0</SelectionColorBluePart>
      <SelectionColorAlphaPart type="int">255</SelectionColorAlphaPart>
      <CanvasColorRedPart type="int">255</CanvasColorRedPart>
      <CanvasColorGreenPart type="int">255</CanvasColorGreenPart>
      <CanvasColorBluePart type="int">255</CanvasColorBluePart>
    </Gui>
  </properties>
{relations_xml}
</qgis>"""

    with open(QGS_PATH, 'w', encoding='utf-8') as f:
        f.write(qgs_content)
    print(f"Generated synchronized QGIS project: {QGS_PATH}")

    # Embed directly in GeoPackage qgis_projects table
    embed_project_in_gpkg(qgs_content)

def embed_project_in_gpkg(qgs_xml):
    """Embeds the QGIS project directly into the qgis_projects table in the GeoPackage"""
    if not os.path.exists(GPKG_PATH):
        print(f"GeoPackage not found at {GPKG_PATH}, skipping embedding.")
        return

    conn = sqlite3.connect(GPKG_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS qgis_projects (
        name TEXT PRIMARY KEY,
        metadata TEXT,
        content BLOB
    );
    ''')
    now_iso = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    meta_json = json.dumps({
        "author": "Mick Morrison",
        "project": "Australian Heritage Landscape Survey & Artefact Recording",
        "created": now_iso,
        "standard": "GDA2020 / OGC GeoPackage 1.2"
    })
    cur.execute('''
    INSERT OR REPLACE INTO qgis_projects (name, metadata, content)
    VALUES ('heritage_survey', ?, ?);
    ''', (meta_json, qgs_xml.encode('utf-8')))
    conn.commit()
    conn.close()
    print("Embedded QGIS project directly into heritage_survey.gpkg (qgis_projects table).")

def main():
    parser = argparse.ArgumentParser(description="Export synchronized QGIS project for Australian Heritage Survey.")
    parser.add_argument('--zone', type=str, default='54', help='MGA2020 Zone (49-56) or "geographic" for EPSG:7844 (default: 54)')
    args = parser.parse_args()

    zone_val = args.zone.strip().lower()
    if zone_val in ('geographic', 'geo', '7844'):
        target_crs_id = 7844
        zone_num = None
    else:
        try:
            zone_num = int(zone_val)
            if not (49 <= zone_num <= 56):
                raise ValueError()
            target_crs_id = 7800 + zone_num
        except ValueError:
            print(f"Error: Invalid zone '{args.zone}'. Expected 49-56 or 'geographic'. Defaulting to 54.")
            zone_num = 54
            target_crs_id = 7854

    export_project(target_crs_id, zone_num)

if __name__ == '__main__':
    main()
