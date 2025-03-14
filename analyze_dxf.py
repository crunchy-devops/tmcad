import ezdxf
import sys
import logging

def get_safe_attribute(entity, attr_name, default=None):
    """Safely get an attribute from a DXF entity."""
    try:
        if hasattr(entity, 'dxf'):
            return getattr(entity.dxf, attr_name, default)
        return default
    except Exception:
        return default

def analyze_text_entities(doc: ezdxf.document.Drawing, layer: str) -> None:
    """Analyze TEXT entities in the specified layer."""
    msp = doc.modelspace()
    text_entities = msp.query(f'TEXT[layer=="{layer}"]')
    
    print(f"\nAnalyzing TEXT entities in layer '{layer}':")
    print(f"Found {len(text_entities)} TEXT entities")
    
    if len(text_entities) == 0:
        return
        
    # Analyze first few entities in detail
    print("\nDetailed analysis of first 5 TEXT entities:")
    for i, entity in enumerate(text_entities[:5]):
        text = get_safe_attribute(entity, 'text', '')
        insert = get_safe_attribute(entity, 'insert', (0,0,0))
        layer = get_safe_attribute(entity, 'layer', '')
        
        print(f"\nTEXT Entity #{i+1}:")
        print(f"  Text content: '{text}'")
        print(f"  Text repr: {repr(text)}")  # Show exact string representation
        print(f"  Text bytes: {[ord(c) for c in text]}")  # Show character codes
        print(f"  Insert point: {insert}")
        print(f"  Layer: {layer}")
        
        # Try to parse elevation
        try:
            cleaned_text = text.strip().replace(',', '.')
            elevation = float(cleaned_text)
            print(f"  Parsed elevation: {elevation}")
        except ValueError:
            print(f"  Failed to parse elevation")

def analyze_dxf(file_path: str) -> None:
    """Analyze the contents of a DXF file."""
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        # Count entities by type and layer
        entity_counts = {}
        layer_entities = {}
        
        for entity in msp:
            # Count by entity type
            entity_type = entity.dxftype()
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
            
            # Count by layer
            layer = get_safe_attribute(entity, 'layer', 'NO_LAYER')
            if layer not in layer_entities:
                layer_entities[layer] = {}
            layer_entities[layer][entity_type] = layer_entities[layer].get(entity_type, 0) + 1
        
        # Print analysis
        print("\n=== DXF File Analysis ===\n")
        
        # Print entity type counts
        print("Entity Types:")
        for entity_type, count in sorted(entity_counts.items()):
            print(f"  {entity_type}: {count}")
        
        # Print layer analysis
        print("\nLayers and Their Entities:\n")
        for layer, entities in sorted(layer_entities.items()):
            print(f"  Layer: {layer}")
            for entity_type, count in sorted(entities.items()):
                print(f"    {entity_type}: {count}")
        
        # Analyze TEXT entities in z value TN layer
        analyze_text_entities(doc, 'z value TN')
        
        # Count total points
        total_points = sum(count for entity_type, count in entity_counts.items() 
                         if entity_type in ['POINT', 'INSERT', 'TCPOINTENTITY'])
        print(f"\nTotal Point Count: {total_points}")
        
    except Exception as e:
        print(f"Error analyzing DXF file: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_dxf.py <dxf_file>", file=sys.stderr)
        sys.exit(1)
        
    analyze_dxf(sys.argv[1])
