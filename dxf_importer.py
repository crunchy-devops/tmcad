import ezdxf
import numpy as np
from typing import List, Optional, Tuple
from point3d import Point3D
from terrain_storage import TerrainManager
from terrain_analysis import TerrainAnalyzer
import re

class DXFPointExtractor:
    """Extract and analyze point clouds from DXF files."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.doc = ezdxf.readfile(filename)
        
    def extract_points(self, layer_name: str = "z value TN") -> List[Point3D]:
        """
        Extract points from specified layer.
        Expects points to be stored as DXF TEXT entities with coordinates.
        """
        points = []
        msp = self.doc.modelspace()
        point_id = 0
        
        # Get all TEXT entities in the specified layer
        for text in msp.query('TEXT[layer=="{}"]'.format(layer_name)):
            try:
                # Extract coordinates from text entity
                x = float(text.dxf.insert[0])
                y = float(text.dxf.insert[1])
                # Try to extract Z value from text content
                z_text = text.dxf.text.strip()
                z = float(z_text)
                
                points.append(Point3D(
                    id=point_id,
                    x=x,
                    y=y,
                    z=z
                ))
                point_id += 1
            except (ValueError, AttributeError) as e:
                print(f"Warning: Skipping invalid point data: {e}")
                
        return points
    
    def create_terrain(self, points: List[Point3D], precision: float = 0.01) -> TerrainManager:
        """Create a TerrainManager from extracted points."""
        terrain = TerrainManager(precision=precision)
        terrain.add_points(points)
        return terrain
    
    def analyze_point_cloud(self, points: List[Point3D]) -> dict:
        """Analyze the extracted point cloud data."""
        if not points:
            return {}
            
        # Convert to numpy array for analysis
        coords = np.array([[p.x, p.y, p.z] for p in points])
        
        # Calculate basic statistics
        stats = {
            'num_points': len(points),
            'bounds': {
                'x': (float(coords[:, 0].min()), float(coords[:, 0].max())),
                'y': (float(coords[:, 1].min()), float(coords[:, 1].max())),
                'z': (float(coords[:, 2].min()), float(coords[:, 2].max()))
            },
            'mean': {
                'x': float(coords[:, 0].mean()),
                'y': float(coords[:, 1].mean()),
                'z': float(coords[:, 2].mean())
            },
            'std': {
                'x': float(coords[:, 0].std()),
                'y': float(coords[:, 1].std()),
                'z': float(coords[:, 2].std())
            }
        }
        
        # Calculate point density
        area = ((stats['bounds']['x'][1] - stats['bounds']['x'][0]) * 
                (stats['bounds']['y'][1] - stats['bounds']['y'][0]))
        stats['point_density'] = len(points) / area if area > 0 else 0
        
        return stats
    
    def process_and_analyze(self, 
                          layer_name: str = "z value TN",
                          precision: float = 0.01,
                          output_file: Optional[str] = None) -> Tuple[TerrainManager, dict]:
        """
        Complete workflow: extract points, create terrain, and analyze.
        Optionally saves to HDF5 file.
        """
        # Extract points
        points = self.extract_points(layer_name)
        if not points:
            raise ValueError(f"No valid points found in layer '{layer_name}'")
            
        # Create terrain
        terrain = self.create_terrain(points, precision)
        
        # Analyze point cloud
        point_stats = self.analyze_point_cloud(points)
        
        # Create analyzer and get terrain features
        analyzer = TerrainAnalyzer(terrain)
        terrain_stats = analyzer.analyze_terrain_features()
        
        # Combine statistics
        stats = {
            'point_cloud': point_stats,
            'terrain_features': terrain_stats
        }
        
        # Save if requested
        if output_file:
            terrain.save_to_hdf5(output_file)
            
        return terrain, stats
