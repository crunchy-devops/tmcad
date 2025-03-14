import ezdxf
import logging
from typing import Dict, List, Set, Tuple

# Standard DXF entity types
STANDARD_ENTITY_TYPES = {
    'POINT', 'LINE', '3DFACE', 'TEXT', 'MTEXT', 'INSERT',
    'CIRCLE', 'ARC', 'ELLIPSE', 'SPLINE', 'POLYLINE',
    'LWPOLYLINE', 'SOLID', 'TRACE', 'MESH', 'HATCH'
}

def analyze_dxf(file_path: str) -> Dict:
    """Analyze DXF file contents and return detailed information."""
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        # Initialize analysis data
        analysis = {
            'entity_types': {},
            'layers': set(),
            'custom_entities': [],
            'point_count': 0,
            'attributes': set(),
            'layer_entities': {}  # Track entities per layer
        }
        
        # Analyze each entity
        for entity in msp:
            # Get entity type
            entity_type = entity.dxftype()
            analysis['entity_types'][entity_type] = analysis['entity_types'].get(entity_type, 0) + 1
            
            # Check if it's a custom entity
            if entity_type not in STANDARD_ENTITY_TYPES:
                entity_info = {
                    'type': entity_type,
                    'attributes': [],
                    'dxf_attributes': [],
                    'sample_data': {}
                }
                
                # Get regular attributes
                for attr in dir(entity):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(entity, attr)
                            if not callable(value):
                                entity_info['attributes'].append(attr)
                                if len(str(value)) < 100:  # Only store small values
                                    entity_info['sample_data'][attr] = str(value)
                        except Exception:
                            pass
                
                # Get DXF attributes
                if hasattr(entity, 'dxf'):
                    for attr in dir(entity.dxf):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(entity.dxf, attr)
                                if not callable(value):
                                    entity_info['dxf_attributes'].append(attr)
                                    if len(str(value)) < 100:  # Only store small values
                                        entity_info['sample_data'][f"dxf.{attr}"] = str(value)
                            except Exception:
                                pass
                
                analysis['custom_entities'].append(entity_info)
            
            # Get layer
            try:
                layer = None
                if hasattr(entity.dxf, 'layer'):
                    layer = entity.dxf.layer
                elif hasattr(entity, 'layer'):
                    layer = entity.layer
                elif hasattr(entity, 'get_dxf_attrib'):
                    layer = entity.get_dxf_attrib('layer', None)
                
                if layer:
                    analysis['layers'].add(layer)
                    if layer not in analysis['layer_entities']:
                        analysis['layer_entities'][layer] = {}
                    layer_stats = analysis['layer_entities'][layer]
                    layer_stats[entity_type] = layer_stats.get(entity_type, 0) + 1
            except Exception:
                pass
            
            # Collect all available attributes
            for attr in dir(entity):
                if not attr.startswith('_'):
                    analysis['attributes'].add(attr)
            
            # Count points
            if entity_type == 'POINT':
                analysis['point_count'] += 1
            elif entity_type == 'LINE':
                analysis['point_count'] += 2
            elif entity_type == '3DFACE':
                analysis['point_count'] += 4
        
        # Convert sets to sorted lists for better readability
        analysis['layers'] = sorted(list(analysis['layers']))
        analysis['attributes'] = sorted(list(analysis['attributes']))
        
        return analysis
        
    except Exception as e:
        logging.error(f"Error analyzing DXF file: {str(e)}")
        raise ValueError(f"Failed to analyze DXF file: {str(e)}")

def print_analysis(analysis: Dict) -> None:
    """Print DXF analysis in a readable format."""
    print("\n=== DXF File Analysis ===")
    
    print("\nEntity Types:")
    for entity_type, count in sorted(analysis['entity_types'].items()):
        print(f"  {entity_type}: {count}")
    
    print("\nLayers and Their Entities:")
    for layer in analysis['layers']:
        print(f"\n  Layer: {layer}")
        if layer in analysis['layer_entities']:
            for entity_type, count in sorted(analysis['layer_entities'][layer].items()):
                print(f"    {entity_type}: {count}")
    
    if analysis['custom_entities']:
        print("\nCustom Entities:")
        for entity in analysis['custom_entities']:
            print(f"\n  Type: {entity['type']}")
            
            if entity['attributes']:
                print("  Regular Attributes:")
                for attr in sorted(entity['attributes']):
                    value = entity['sample_data'].get(attr, '')
                    print(f"    {attr}: {value}")
            
            if entity['dxf_attributes']:
                print("  DXF Attributes:")
                for attr in sorted(entity['dxf_attributes']):
                    value = entity['sample_data'].get(f"dxf.{attr}", '')
                    print(f"    {attr}: {value}")
    
    print(f"\nTotal Point Count: {analysis['point_count']}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python analyze_dxf.py <dxf_file>")
        sys.exit(1)
        
    try:
        analysis = analyze_dxf(sys.argv[1])
        print_analysis(analysis)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
