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
            layers = [layer.dxf.name for layer in doc.layers]
            self.logger.info(f"Found {len(layers)} layers in {file_path}")
            return layers
        except Exception as e:
            self.logger.error(f"Error reading layers from DXF: {str(e)}")
            raise ValueError(f"Failed to read DXF file: {str(e)}")

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
                layers = [layer.dxf.name for layer in doc.layers]
            
            self.logger.info(f"Importing terrain from layers: {layers}")
            
            # Process each entity in specified layers
            for entity in msp:
                if entity.dxf.layer not in layers:
                    continue
                    
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
            
            if len(terrain.points) == 0:
                raise ValueError(f"No points found in layers: {layers}")
                
            # Compute surface metrics
            terrain.compute_surface_metrics()
            
            self.logger.info(f"Successfully imported {len(terrain.points)} points from {len(layers)} layers")
            return terrain
            
        except Exception as e:
            self.logger.error(f"Error importing terrain: {str(e)}")
            raise ValueError(f"Failed to import terrain: {str(e)}")
