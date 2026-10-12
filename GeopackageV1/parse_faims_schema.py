#!/usr/bin/env python3
"""
parse_faims_schema.py

Extracts all FAIMS 2 module definitions, UI layouts, field rules, 
and controlled vocabularies from Australian-heritage-survey-and-artefact-recording-schema.
Outputs standardized generic JSON schemas for GeoPackage generation and QGIS forms.
"""

import os
import glob
import json
import re
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_DIR = os.path.join(BASE_DIR, 'vocab')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema')

def parse_vocabularies():
    """Parses all 111 XML vocabulary files in vocab/"""
    vocabularies = {}
    vocab_files = sorted(glob.glob(os.path.join(VOCAB_DIR, '*.xml')))
    
    for vpath in vocab_files:
        vname = os.path.splitext(os.path.basename(vpath))[0]
        try:
            tree = ET.parse(vpath)
            root = tree.getroot()
        except Exception as e:
            print(f"Error parsing vocab {vpath}: {e}")
            continue

        options = []
        for opt in root.findall('opt'):
            # Check if this opt has nested opt children (hierarchical)
            child_opts = opt.findall('opt')
            if child_opts:
                parent_text = (opt.text or '').strip()
                for c_opt in child_opts:
                    c_text = (c_opt.text or '').strip()
                    desc_elem = c_opt.find('desc')
                    desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ''
                    options.append({
                        'value': c_text,
                        'parent': parent_text,
                        'desc': desc
                    })
            else:
                text = (opt.text or '').strip()
                desc_elem = opt.find('desc')
                desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ''
                options.append({
                    'value': text,
                    'parent': None,
                    'desc': desc
                })

        vocabularies[vname] = {
            'name': vname,
            'title': vname.replace('_', ' ').title(),
            'options': options
        }

    return vocabularies

def parse_module_schemas(vocabularies):
    """
    Parses module.xml and data_schema.xml across Phase 1 and Phase 2 modules.
    Merges layout, labels, flags, types, descriptions, and vocabularies.
    Removes legacy 'Coordinate' boundary points as polygons are now digitized natively.
    """
    modules = {}
    module_files = sorted(glob.glob(os.path.join(BASE_DIR, 'Phase*/**/module.xml'), recursive=True))

    for mpath in module_files:
        mod_dir = os.path.dirname(mpath)
        mod_name = os.path.basename(mod_dir)
        
        with open(mpath, 'r', encoding='utf-8') as f:
            raw_xml = f.read()

        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        try:
            root = ET.fromstring(raw_xml, parser=parser)
        except Exception as e:
            print(f"Error parsing module.xml in {mod_name}: {e}")
            continue

        # Check if data_schema.xml exists in module/
        ds_path = os.path.join(mod_dir, 'module', 'data_schema.xml')
        ds_properties = {}
        if os.path.exists(ds_path):
            try:
                ds_tree = ET.parse(ds_path)
                ds_root = ds_tree.getroot()
                for arch_el in ds_root.findall('.//ArchaeologicalElement'):
                    el_name = arch_el.attrib.get('name', '')
                    for prop in arch_el.findall('property'):
                        p_name = prop.attrib.get('name', '')
                        terms = []
                        lookup = prop.find('lookup')
                        if lookup is not None:
                            for term in lookup.findall('term'):
                                t_text = term.text or ''
                                t_lines = t_text.strip().split('\n')
                                val = t_lines[0].strip().strip('{}')
                                desc_el = term.find('description')
                                desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ''
                                terms.append({'value': val.replace('_', ' '), 'desc': desc})
                        ds_properties[(el_name, p_name)] = {
                            'type': prop.attrib.get('type', ''),
                            'isIdentifier': prop.attrib.get('isIdentifier', 'false') == 'true',
                            'formatString': prop.findtext('formatString', ''),
                            'terms': terms
                        }
            except Exception as e:
                print(f"Error reading data_schema.xml in {mod_name}: {e}")

        entities = {}

        for child in root:
            if not isinstance(child.tag, str) or child.tag in ('User_List', 'Control', 'logic', 'css'):
                continue
            
            ent_name = child.tag

            # Legacy boundary points entity: remove as requested
            if ent_name == 'Coordinate':
                continue

            fmt_elem = child.find('fmt')
            id_format = fmt_elem.text if fmt_elem is not None else ''

            # Determine entity ID prefix (e.g. BUR from BUR{{Burial_ID}})
            id_prefix = ''
            if id_format:
                m = re.match(r'^([A-Z_]+)\{\{', id_format)
                if m:
                    id_prefix = m.group(1)
                else:
                    parts = re.findall(r'([A-Z]+)\{\{', id_format)
                    if parts:
                        id_prefix = parts[-1]

            tabs = {}
            for tab in child:
                if not isinstance(tab.tag, str) or tab.tag == 'fmt':
                    continue
                tab_name = tab.tag
                fields = []
                
                prev_comment = None
                for elem in tab:
                    if not isinstance(elem.tag, str):
                        prev_comment = elem.text
                        continue
                    
                    fname = elem.tag

                    # Skip legacy boundary coordinate action buttons/links
                    if fname in ('Record_coordinate', 'List_of_related_coordinates', 'New_coordinate', 'List_of_related_scars', 'New_scar'):
                        continue

                    attrs = dict(elem.attrib)
                    
                    desc_text = ''
                    inner_comment = ''
                    for sub in elem:
                        if not isinstance(sub.tag, str):
                            inner_comment = sub.text
                        elif sub.tag == 'desc':
                            desc_text = sub.text.strip() if sub.text else ''
                    
                    vocab_source = ''
                    for c in [inner_comment, prev_comment]:
                        if c and '@SOURCE:' in c:
                            m = re.search(r'@SOURCE:\s*([^\s>]+)', c)
                            if m:
                                vocab_source = os.path.splitext(os.path.basename(m.group(1)))[0]

                    raw_text = elem.text.strip() if elem.text and elem.text.strip() else ''
                    label = raw_text if raw_text and not raw_text.startswith('{') else fname.replace('_', ' ')
                    
                    widget_type = attrs.get('t', '')
                    base_type = attrs.get('b', '')
                    flags_str = attrs.get('f', '')
                    flags = flags_str.split() if flags_str else []

                    if widget_type:
                        field_type = widget_type
                    elif base_type:
                        field_type = base_type
                    elif vocab_source or (fname.lower() in vocabularies):
                        field_type = 'dropdown'
                    elif 'autonum' in flags:
                        field_type = 'autonum'
                    else:
                        field_type = 'text'

                    matched_vocab = None
                    if vocab_source and vocab_source in vocabularies:
                        matched_vocab = vocab_source
                    elif fname.lower() in vocabularies:
                        matched_vocab = fname.lower()

                    options = []
                    if matched_vocab and matched_vocab in vocabularies:
                        options = vocabularies[matched_vocab]['options']
                    else:
                        clean_prop_name = fname.replace('_', ' ')
                        for (ds_ent, ds_prop), pdata in ds_properties.items():
                            if ds_prop.lower() == clean_prop_name.lower() and pdata['terms']:
                                options = pdata['terms']
                                break

                    markdown_content = ''
                    md_elem = elem.find('markdown')
                    if md_elem is not None and md_elem.text:
                        markdown_content = md_elem.text.strip()

                    fields.append({
                        'name': fname,
                        'label': label,
                        'type': field_type,
                        'base_type': base_type,
                        'flags': flags,
                        'desc': desc_text,
                        'vocab_ref': matched_vocab,
                        'options': options,
                        'inherited_from': attrs.get('i', ''),
                        'link_create': attrs.get('lc', ''),
                        'link_entity': attrs.get('ec', ''),
                        'markdown': markdown_content
                    })
                    prev_comment = None

                tabs[tab_name] = fields

            is_child = (ent_name == 'Scar')
            parent_entity = 'Tree' if ent_name == 'Scar' else None

            entities[ent_name] = {
                'name': ent_name,
                'label': ent_name.replace('_', ' '),
                'module': mod_name,
                'id_format': id_format,
                'id_prefix': id_prefix,
                'is_child': is_child,
                'parent_entity': parent_entity,
                'tabs': tabs
            }

        modules[mod_name] = {
            'module_name': mod_name,
            'entities': entities
        }

    return modules

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Parsing controlled vocabularies...")
    vocabularies = parse_vocabularies()
    print(f"Loaded {len(vocabularies)} vocabularies.")
    
    vocab_output_path = os.path.join(OUTPUT_DIR, 'vocabularies.json')
    with open(vocab_output_path, 'w', encoding='utf-8') as f:
        json.dump(vocabularies, f, indent=2)
    print(f"Saved vocabularies to {vocab_output_path}")

    print("Parsing module schemas...")
    modules = parse_module_schemas(vocabularies)
    
    all_entities = {}
    for mod_name, mod_info in modules.items():
        for ent_name, ent_info in mod_info['entities'].items():
            all_entities[ent_name] = ent_info

    schema_output_path = os.path.join(OUTPUT_DIR, 'faims_extracted_schema.json')
    with open(schema_output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'modules': modules,
            'entities': all_entities,
            'total_entities': len(all_entities)
        }, f, indent=2)
    print(f"Saved extracted schema ({len(all_entities)} entities) to {schema_output_path}")

if __name__ == '__main__':
    main()
