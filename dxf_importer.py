from __future__ import annotations
import ezdxf
import logging
from typing import Optional, List, Dict, Set
from point3d import Point3D
from terrain_model import TerrainModel

class DXFImporter:
    """Imports terrain data from DXF files with memory-efficient point handling."""
    
    def __init__(self):
        """Initialize DXF importer with default settings."""
        self.logger = logging.getLogger(__name__)
        self._next_point_id = 1
        self._processed_points: Set[tuple] = set()  # Track unique points by coordinates

    def import_terrain(self, file_path: str, model_name: Optional[str] = None) -> TerrainModel:
        """
        Import terrain data from DXF file.
        
        Args:
            file_path: Path to DXF file
            model_name: Optional name for terrain model, defaults to filename
            
        Returns:
            TerrainModel containing imported terrain data
            
        Raises:
            ValueError: If file cannot be read or contains no valid terrain data
        """
        try:
            # Open and validate DXF file
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            # Extract or generate model name
            if not model_name:
                model_name = file_path.split('\\')[-1].replace('.dxf', '')
            
            # Create terrain model
            terrain = TerrainModel(model_name)
            
            # Process entities by type
            self._process_points(msp, terrain)
            self._process_3dfaces(msp, terrain)
            self._process_polylines(msp, terrain)
            
            if len(terrain.points) == 0:
                raise ValueError("No valid terrain points found in DXF file")
                
            self.logger.info(f"Successfully imported {len(terrain.points)} points from {file_path}")
            return terrain
            
        except ezdxf.DXFError as e:
            error_msg = f"Failed to read DXF file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error importing terrain from {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        finally:
            # Clear processed points set to free memory
            self._processed_points.clear()

    def _add_point(self, terrain: TerrainModel, x: float, y: float, z: float) -> None:
        """
        Add point to terrain model if not already processed.
        Uses coordinate-based deduplication.
        """
        # Round coordinates for stable comparison
        rx, ry, rz = round(x, 6), round(y, 6), round(z, 6)
        point_key = (rx, ry, rz)
        
        if point_key not in self._processed_points:
            self._processed_points.add(point_key)
            point = Point3D(id=self._next_point_id, x=x, y=y, z=z)
            terrain.add_point(point)
            self._next_point_id += 1

    def _process_points(self, msp, terrain: TerrainModel) -> None:
        """Process POINT entities."""
        for point in msp.query('POINT'):
            x, y, z = point.dxf.location
            self._add_point(terrain, x, y, z)

    def _process_3dfaces(self, msp, terrain: TerrainModel) -> None:
        """Process 3DFACE entities."""
        for face in msp.query('3DFACE'):
            # Get unique vertices (some may be duplicated for triangles)
            vertices = set()
            for i in range(4):
                vertex = getattr(face.dxf, f'vtx{i}')
                if vertex != (0, 0, 0):  # Skip null vertices
                    vertices.add((vertex[0], vertex[1], vertex[2]))
            
            # Add vertices as points
            for x, y, z in vertices:
                self._add_point(terrain, x, y, z)

    def _process_polylines(self, msp, terrain: TerrainModel) -> None:
        """Process POLYLINE and LWPOLYLINE entities."""
        # Process regular polylines
        for pline in msp.query('POLYLINE'):
            if pline.dxf.flags & 8:  # 3D polyline
                for vertex in pline.points():
                    x, y, z = vertex
                    self._add_point(terrain, x, y, z)
        
        # Process lightweight polylines
        for lwpline in msp.query('LWPOLYLINE'):
            # LWPOLYLINE vertices are always 2D, skip if no elevation
            if hasattr(lwpline.dxf, 'elevation'):
                z = lwpline.dxf.elevation
                for vertex in lwpline.get_points():
                    x, y = vertex[:2]
                    self._add_point(terrain, x, y, z)
