import ezdxf
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_dxf(file_path: str, target_layer: str):
    """Analyze entities in a specific layer of a DXF file."""
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        logger.info(f"Analyzing layer: {target_layer}")
        
        # Count entities by type in the target layer
        entity_types = {}
        
        for entity in msp:
            try:
                # Get entity layer and type
                layer = getattr(entity, 'dxf', None)
                if layer:
                    layer = getattr(layer, 'layer', None)
                
                if layer == target_layer:
                    dxftype = entity.dxftype()
                    entity_types[dxftype] = entity_types.get(dxftype, 0) + 1
                    
                    # Print detailed info for each entity
                    logger.info(f"\nEntity Type: {dxftype}")
                    
                    # Get all DXF attributes
                    for attr in dir(entity.dxf):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(entity.dxf, attr)
                                logger.info(f"  {attr}: {value}")
                            except Exception:
                                pass
                    
                    # Special handling for text entities
                    if dxftype in ('TEXT', 'MTEXT'):
                        text = getattr(entity.dxf, 'text', None) or getattr(entity, 'text', None)
                        logger.info(f"  text content: {text}")
                    
            except Exception as e:
                logger.warning(f"Error analyzing entity: {str(e)}")
        
        logger.info("\nEntity count by type:")
        for etype, count in entity_types.items():
            logger.info(f"{etype}: {count}")
            
    except Exception as e:
        logger.error(f"Error analyzing DXF file: {str(e)}")

if __name__ == '__main__':
    analyze_dxf('data/plan-masse.dxf', 'z value TN')
