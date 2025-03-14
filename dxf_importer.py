import logging
import ezdxf
import numpy as np
from typing import List, Optional, Set, Dict, Tuple
from terrain_model import TerrainModel
from point3d import Point3D, PointCloud

class DXFImporter:
    """Import terrain data from DXF files."""
    
    _next_point_id = 1  # Class-level counter for point IDs
    logger = logging.getLogger(__name__)  # Class-level logger
    logger.setLevel(logging.DEBUG)

    @classmethod
    def get_layers(cls, file_path: str) -> List[str]:
        """Get list of available layers in the DXF file."""
        try:
            doc = ezdxf.readfile(file_path)
            # Get all unique layer names from entities
            layers = set()
            msp = doc.modelspace()
            for entity in msp:
                try:
                    # Try different ways to get layer information
                    layer = None
                    if hasattr(entity.dxf, 'layer'):
                        layer = entity.dxf.layer
                    elif hasattr(entity, 'layer'):
                        layer = entity.layer
                    elif hasattr(entity, 'get_dxf_attrib'):
                        layer = entity.get_dxf_attrib('layer', None)
                    
                    if layer:
                        layers.add(layer)
                except Exception:
                    # Skip entities without layer attribute
                    continue
            
            layers = sorted(list(layers))
            cls.logger.info(f"Found {len(layers)} layers in {file_path}")
            return layers
        except Exception as e:
            cls.logger.error(f"Error reading layers from DXF: {str(e)}")
            raise ValueError(f"Failed to read DXF file: {str(e)}")

    @classmethod
    def _extract_text_elevation(cls, text_entity) -> Optional[Tuple[float, float, float]]:
        """Extract point coordinates from a TEXT entity."""
        try:
            # Get x,y coordinates from insert point
            if hasattr(text_entity, 'dxf') and hasattr(text_entity.dxf, 'insert'):
                point = text_entity.dxf.insert
                # Handle both tuple/list and DXF point types
                try:
                    x = float(point[0])
                    y = float(point[1])
                    cls.logger.debug(f"Using insert point coordinates: ({x}, {y})")
                except (TypeError, IndexError) as e:
                    cls.logger.debug(f"Failed to extract insert point coordinates: {e}")
                    return None
            else:
                cls.logger.debug("Text entity missing insert point")
                return None

            # Get elevation from text content
            if not hasattr(text_entity, 'dxf') or not hasattr(text_entity.dxf, 'text'):
                cls.logger.debug("Text entity missing text content")
                return None
                
            text = text_entity.dxf.text
            if not text:
                cls.logger.debug("Empty text content")
                return None

            # Log raw text content for debugging
            cls.logger.debug(f"Raw text content: '{text}'")
            cls.logger.debug(f"Text bytes: {[ord(c) for c in text]}")

            # Clean and parse the elevation value
            # Remove any non-printable characters and whitespace
            text = ''.join(c for c in text if c.isprintable()).strip()
            cls.logger.debug(f"After cleaning non-printable: '{text}'")
            
            # Clean up the text and handle decimal separator
            text = text.replace(',', '.').strip()
            cls.logger.debug(f"After cleaning separators: '{text}'")
            
            # Try to parse as float - this will be our z value
            try:
                z = float(text)
                cls.logger.debug(f"Successfully parsed elevation {z} from text: '{text_entity.dxf.text}' at ({x:.2f}, {y:.2f})")
                return (x, y, z)
            except ValueError as ve:
                cls.logger.debug(f"Failed to parse elevation from text: '{text}', error: {str(ve)}")
                return None

        except Exception as e:
            cls.logger.debug(f"Error extracting text elevation: {str(e)}")
            return None

    @classmethod
    def _extract_point_elevation(cls, point_entity) -> Optional[Tuple[float, float, float]]:
        """Extract point coordinates from a TCPOINTENTITY."""
        try:
            # Get coordinates from point entity
            if hasattr(point_entity, 'dxf'):
                # Try to get coordinates from common attributes
                coords = None
                if hasattr(point_entity.dxf, 'location'):
                    coords = point_entity.dxf.location
                elif hasattr(point_entity.dxf, 'point'):
                    coords = point_entity.dxf.point
                elif hasattr(point_entity.dxf, 'position'):
                    coords = point_entity.dxf.position
                elif hasattr(point_entity.dxf, 'insert'):
                    coords = point_entity.dxf.insert
                
                if coords:
                    try:
                        x = float(coords[0])
                        y = float(coords[1])
                        z = float(coords[2])
                        cls.logger.debug(f"Extracted point coordinates: ({x:.2f}, {y:.2f}, {z:.2f})")
                        return (x, y, z)
                    except (TypeError, IndexError) as e:
                        cls.logger.debug(f"Failed to extract point coordinates: {e}")
                        return None
                    
            return None

        except Exception as e:
            cls.logger.debug(f"Error extracting point coordinates: {str(e)}")
            return None

    @classmethod
    def import_terrain(cls, file_path: str, model_name: Optional[str] = None, layers: Optional[List[str]] = None) -> TerrainModel:
        """Import terrain points from TEXT and TCPOINTENTITY entities in the specified layers."""
        if not model_name:
            raise ValueError("Model name is required")

        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            # Create terrain model
            terrain = TerrainModel(model_name)
            points_added = set()
            
            # Use default layer if none specified
            if not layers:
                layers = ['z value TN']
            
            for layer in layers:
                cls.logger.info(f"Processing layer: {layer}")
                
                # Query TEXT entities in the current layer
                text_entities = msp.query(f'TEXT[layer=="{layer}"]')
                cls.logger.info(f"Found {len(text_entities)} TEXT entities in layer '{layer}'")
                
                # Process TEXT entities
                for entity in text_entities:
                    try:
                        coords = cls._extract_text_elevation(entity)
                        if coords:
                            x, y, z = coords
                            point_key = (round(x, 3), round(y, 3))  # Use rounded x,y as key to avoid floating point issues
                            if point_key not in points_added:
                                point = Point3D(id=cls._next_point_id, x=x, y=y, z=z)
                                cls._next_point_id += 1
                                terrain.add_point(point)
                                points_added.add(point_key)
                                cls.logger.debug(f"Added point from TEXT at ({x:.2f}, {y:.2f}, {z:.2f})")
                    except Exception as e:
                        cls.logger.debug(f"Error processing TEXT entity: {str(e)}")
                        continue
                
                # Query TCPOINTENTITY entities in the current layer
                point_entities = msp.query(f'TCPOINTENTITY[layer=="{layer}"]')
                cls.logger.info(f"Found {len(point_entities)} TCPOINTENTITY entities in layer '{layer}'")
                
                # Process TCPOINTENTITY entities
                for entity in point_entities:
                    try:
                        coords = cls._extract_point_elevation(entity)
                        if coords:
                            x, y, z = coords
                            point_key = (round(x, 3), round(y, 3))  # Use rounded x,y as key
                            if point_key not in points_added:
                                point = Point3D(id=cls._next_point_id, x=x, y=y, z=z)
                                cls._next_point_id += 1
                                terrain.add_point(point)
                                points_added.add(point_key)
                                cls.logger.debug(f"Added point from TCPOINTENTITY at ({x:.2f}, {y:.2f}, {z:.2f})")
                    except Exception as e:
                        cls.logger.debug(f"Error processing TCPOINTENTITY: {str(e)}")
                        continue
            
            if len(terrain.points) == 0:
                raise ValueError(f"No valid elevation points found in layers: {layers}")
                
            # Compute surface metrics
            terrain.compute_surface_metrics()
            
            cls.logger.info(f"Successfully imported {len(terrain.points)} points from layers {layers}")
            return terrain
            
        except Exception as e:
            cls.logger.error(f"Error importing terrain: {str(e)}")
            raise ValueError(f"Failed to import terrain: {str(e)}")
