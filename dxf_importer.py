import logging
import ezdxf
import numpy as np
from typing import List, Optional, Set, Dict, Tuple
from terrain_model import TerrainModel
from point3d import Point3D, PointCloud

class DXFImporter:
    """Import terrain data from DXF files."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_layers(self, file_path: str) -> List[str]:
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
            self.logger.info(f"Found {len(layers)} layers in {file_path}")
            return layers
        except Exception as e:
            self.logger.error(f"Error reading layers from DXF: {str(e)}")
            raise ValueError(f"Failed to read DXF file: {str(e)}")

    def _extract_point_coordinates(self, entity) -> Optional[Tuple[float, float, float]]:
        """Extract point coordinates from an entity using various methods."""
        try:
            # Special handling for TEXT entities
            if entity.dxftype() in ('TEXT', 'MTEXT'):
                # Get text position
                x = y = z = None
                
                # Try to get position from insert_point (TEXT) or insert (MTEXT)
                if hasattr(entity.dxf, 'insert_point'):
                    point = entity.dxf.insert_point
                    if isinstance(point, (tuple, list)) and len(point) >= 2:
                        x, y = point[:2]
                        z = point[2] if len(point) > 2 else 0
                elif hasattr(entity.dxf, 'insert'):
                    point = entity.dxf.insert
                    if isinstance(point, (tuple, list)) and len(point) >= 2:
                        x, y = point[:2]
                        z = point[2] if len(point) > 2 else 0
                
                # If we found x,y coordinates but no z, try to get z from text content
                if x is not None and y is not None:
                    if z is None:
                        try:
                            # Get text content
                            text = entity.dxf.text if hasattr(entity.dxf, 'text') else None
                            if text:
                                # Try to parse z value from text
                                # Remove common prefixes and handle different number formats
                                text = text.replace(',', '.').strip()
                                text = text.replace('Z=', '').replace('z=', '').strip()
                                text = text.replace('H=', '').replace('h=', '').strip()
                                text = text.replace('E=', '').replace('e=', '').strip()
                                text = text.replace('N=', '').replace('n=', '').strip()
                                z = float(text)
                        except (ValueError, AttributeError):
                            z = 0  # Default z value if text parsing fails
                    
                    return (x, y, z)
            
            # Try different ways to get point coordinates
            if hasattr(entity, 'get_points'):
                points = entity.get_points()
                if points and len(points) > 0:
                    point = points[0]
                    if isinstance(point, (tuple, list)) and len(point) >= 3:
                        return tuple(point[:3])
            
            if hasattr(entity, 'coordinates'):
                coords = entity.coordinates
                if isinstance(coords, (tuple, list)) and len(coords) >= 3:
                    return tuple(coords[:3])
            
            if hasattr(entity.dxf, 'location'):
                loc = entity.dxf.location
                if isinstance(loc, (tuple, list)) and len(loc) >= 3:
                    return tuple(loc[:3])
            
            if all(hasattr(entity.dxf, attr) for attr in ['x', 'y', 'z']):
                return (entity.dxf.x, entity.dxf.y, entity.dxf.z)
            
            # Special handling for TCPOINTENTITY
            if entity.dxftype() == 'TCPOINTENTITY':
                # Try to get coordinates from base class tags
                if hasattr(entity, 'base_class'):
                    for tag in entity.base_class:
                        # Look for coordinate tags (group codes 10, 20, 30 for x,y,z)
                        if isinstance(tag.value, (tuple, list)) and len(tag.value) >= 3:
                            return tuple(tag.value[:3])
                        elif tag.code == 10:  # X coordinate
                            x = float(tag.value)
                            # Look for Y and Z in subsequent tags
                            for i, next_tag in enumerate(entity.base_class[entity.base_class.index(tag)+1:]):
                                if next_tag.code == 20:  # Y coordinate
                                    y = float(next_tag.value)
                                    for z_tag in entity.base_class[entity.base_class.index(next_tag)+1:]:
                                        if z_tag.code == 30:  # Z coordinate
                                            z = float(z_tag.value)
                                            return (x, y, z)
                                    break
                            break
                
                # Try to get coordinates from extended data
                if hasattr(entity, 'xdata'):
                    for tag in entity.xdata:
                        if isinstance(tag.value, (tuple, list)) and len(tag.value) >= 3:
                            return tuple(tag.value[:3])
                
                # Try to get coordinates from entity data
                if hasattr(entity, 'data'):
                    data = entity.data
                    if isinstance(data, dict) and 'position' in data:
                        pos = data['position']
                        if isinstance(pos, (tuple, list)) and len(pos) >= 3:
                            return tuple(pos[:3])
                
                # Try to get coordinates from extended tags
                if hasattr(entity, 'xtags'):
                    for tag in entity.xtags:
                        if isinstance(tag.value, (tuple, list)) and len(tag.value) >= 3:
                            return tuple(tag.value[:3])
                        elif tag.code == 10:  # X coordinate
                            x = float(tag.value)
                            # Look for Y and Z in subsequent tags
                            for i, next_tag in enumerate(entity.xtags[entity.xtags.index(tag)+1:]):
                                if next_tag.code == 20:  # Y coordinate
                                    y = float(next_tag.value)
                                    for z_tag in entity.xtags[entity.xtags.index(next_tag)+1:]:
                                        if z_tag.code == 30:  # Z coordinate
                                            z = float(z_tag.value)
                                            return (x, y, z)
                                    break
                            break
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error extracting coordinates: {str(e)}")
            return None

    def import_terrain(self, file_path: str, model_name: str, layers: Optional[List[str]] = None) -> TerrainModel:
        """Import terrain from DXF file with specified layers."""
        if not model_name:
            raise ValueError("Model name is required")

        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            # Create terrain model
            terrain = TerrainModel(model_name)
            points_added = set()
            
            # If no layers specified, use all layers
            if not layers:
                layers = self.get_layers(file_path)
            
            self.logger.info(f"Importing terrain from layers: {layers}")
            
            # Process each entity in specified layers
            for entity in msp:
                try:
                    # Try different ways to get layer information
                    entity_layer = None
                    if hasattr(entity.dxf, 'layer'):
                        entity_layer = entity.dxf.layer
                    elif hasattr(entity, 'layer'):
                        entity_layer = entity.layer
                    elif hasattr(entity, 'get_dxf_attrib'):
                        entity_layer = entity.get_dxf_attrib('layer', None)
                    
                    if not entity_layer or entity_layer not in layers:
                        continue
                    
                    # Log entity type and layer for debugging
                    self.logger.debug(f"Processing {entity.dxftype()} in layer {entity_layer}")
                        
                    # Handle standard DXF entities
                    if entity.dxftype() == 'POINT':
                        x, y, z = entity.dxf.location
                        if (x, y, z) not in points_added:
                            terrain.add_point(x, y, z)
                            points_added.add((x, y, z))
                            
                    elif entity.dxftype() == 'LINE':
                        start = entity.dxf.start
                        end = entity.dxf.end
                        if (start.x, start.y, start.z) not in points_added:
                            terrain.add_point(start.x, start.y, start.z)
                            points_added.add((start.x, start.y, start.z))
                        if (end.x, end.y, end.z) not in points_added:
                            terrain.add_point(end.x, end.y, end.z)
                            points_added.add((end.x, end.y, end.z))
                            
                    elif entity.dxftype() == '3DFACE':
                        for i in range(4):
                            point = (entity.dxf.vtx0, entity.dxf.vtx1, 
                                   entity.dxf.vtx2, entity.dxf.vtx3)[i]
                            if (point.x, point.y, point.z) not in points_added:
                                terrain.add_point(point.x, point.y, point.z)
                                points_added.add((point.x, point.y, point.z))
                                
                    # Handle text and other entities
                    else:
                        coords = self._extract_point_coordinates(entity)
                        if coords and coords not in points_added:
                            terrain.add_point(*coords)
                            points_added.add(coords)
                                
                except Exception as e:
                    # Log the error but continue processing other entities
                    self.logger.debug(f"Error processing entity: {str(e)}")
                    continue
            
            if len(terrain.points) == 0:
                raise ValueError(f"No points found in layers: {layers}")
                
            # Compute surface metrics
            terrain.compute_surface_metrics()
            
            self.logger.info(f"Successfully imported {len(terrain.points)} points from {len(layers)} layers")
            return terrain
            
        except Exception as e:
            self.logger.error(f"Error importing terrain: {str(e)}")
            raise ValueError(f"Failed to import terrain: {str(e)}")
