"""
DXF to Point3D converter module.

This module provides functionality to convert DXF text entities from
any layer into Point3D objects for terrain modeling.
"""

from typing import List, Optional, Set
import ezdxf
from ezdxf.document import Drawing
from ezdxf.entities import Text
from point3d import Point3D

class DxfConversionError(Exception):
    """Exception raised for errors during DXF conversion."""
    pass

class DxfConverter:
    """Converts DXF text entities to Point3D objects.
    
    This class handles the conversion of text entities from DXF files into
    Point3D objects. Each text entity represents a point with X,Y coordinates
    from its insertion point and Z value from its text content.
    
    Memory Usage:
        - Point3D objects: 32 bytes per point
        - Temporary storage during conversion: O(n) where n is number of points
        
    Performance:
        - File loading: O(1)
        - Layer scanning: O(m) where m is number of text entities
        - Point conversion: O(n) where n is number of points
        - Memory efficient using Point3D's optimized representation
    """
    
    def __init__(self):
        """Initialize the DXF converter."""
        self._next_id = 1
    
    def get_text_layers(self, filepath: str) -> List[str]:
        """Get all layers containing TEXT entities in the DXF file.
        
        Args:
            filepath: Path to DXF file to analyze
            
        Returns:
            List of layer names containing TEXT entities
            
        Raises:
            DxfConversionError: If file cannot be read or processed
        """
        try:
            doc: Drawing = ezdxf.readfile(filepath)
            msp = doc.modelspace()
            
            # Query all text entities
            text_list = list(msp.query('TEXT'))
            
            # Extract unique layer names
            layers = {text.dxf.layer for text in text_list}
            return sorted(list(layers))
            
        except ezdxf.DXFError as e:
            raise DxfConversionError(f"Failed to read DXF file: {e}")
        except IOError as e:
            raise DxfConversionError(f"Failed to open file: {e}")
    
    def _convert_text_to_point(self, text: Text, id: Optional[int] = None) -> Point3D:
        """Convert a single DXF text entity to a Point3D.
        
        Args:
            text: DXF text entity containing point information
            id: Optional point ID, will use auto-incrementing ID if not provided
            
        Returns:
            Point3D object with coordinates from text entity
            
        Raises:
            DxfConversionError: If Z value text cannot be converted to float
        """
        if id is None:
            id = self._next_id
            self._next_id += 1
            
        try:
            z_value = float(text.dxf.text)
        except ValueError:
            raise DxfConversionError(
                f"Invalid Z value text: '{text.dxf.text}' in layer '{text.dxf.layer}'"
            )
            
        return Point3D(
            id=id,
            x=text.dxf.insert.x,
            y=text.dxf.insert.y,
            z=z_value
        )
    
    def _convert_texts_to_points(self, texts: List[Text]) -> List[Point3D]:
        """Convert multiple DXF text entities to Point3D objects.
        
        Args:
            texts: List of DXF text entities to convert
            
        Returns:
            List of Point3D objects
            
        Note:
            Uses auto-incrementing IDs starting from current _next_id value
        """
        points = []
        for text in texts:
            try:
                point = self._convert_text_to_point(text)
                points.append(point)
            except DxfConversionError:
                # Skip invalid points but continue processing
                continue
        return points
    
    def _query_texts_from_layers(self, msp, layers: Optional[List[str]] = None) -> List[Text]:
        """Query text entities from specified layers.
        
        Args:
            msp: DXF modelspace to query
            layers: List of layer names to query, or None for all layers
            
        Returns:
            List of text entities from specified layers
        """
        if not layers:
            return list(msp.query('TEXT'))
            
        # Query each layer separately and combine results
        texts = []
        for layer in layers:
            layer_texts = list(msp.query(f'TEXT[layer=="{layer}"]'))
            texts.extend(layer_texts)
        return texts
    
    def load_points_from_file(self, filepath: str, layer: Optional[str] = None, 
                            layers: Optional[List[str]] = None) -> List[Point3D]:
        """Load points from specified layers in a DXF file.
        
        Args:
            filepath: Path to DXF file to process
            layer: Single layer name to process (deprecated, use layers instead)
            layers: List of layer names to process, or None to process all layers
            
        Returns:
            List of Point3D objects from text entities
            
        Raises:
            DxfConversionError: If file cannot be read or processed
            
        Note:
            If both layer and layers are provided, layers takes precedence
        """
        try:
            doc: Drawing = ezdxf.readfile(filepath)
            msp = doc.modelspace()
            
            # Handle legacy single layer parameter
            if layers is None and layer is not None:
                layers = [layer]
            
            # Query text entities from layers
            text_list = self._query_texts_from_layers(msp, layers)
            
            # Convert to points
            return self._convert_texts_to_points(text_list)
            
        except ezdxf.DXFError as e:
            raise DxfConversionError(f"Failed to read DXF file: {e}")
        except IOError as e:
            raise DxfConversionError(f"Failed to open file: {e}")
