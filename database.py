from __future__ import annotations
import os
import json
import logging
import struct
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Set
from terrain_model import TerrainModel
from point3d import Point3D, PointCloud

class Database:
    """Memory-efficient terrain model database with binary storage."""
    
    def __init__(self, base_dir: str = 'data'):
        """Initialize database with specified base directory."""
        self.logger = logging.getLogger(__name__)
        self.base_dir = base_dir
        self._ensure_dirs_exist()
        
        # Cache for frequently accessed terrains
        self._terrain_cache: Dict[str, TerrainModel] = {}
        self._max_cache_size = 5  # Maximum number of terrains to keep in memory
        
    def _ensure_dirs_exist(self) -> None:
        """Ensure required directories exist."""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'points'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'metadata'), exist_ok=True)

    def save_terrain(self, terrain: TerrainModel) -> None:
        """Save a terrain model to the database."""
        if not terrain.name:
            raise ValueError("Terrain model must have a name")
        
        # Create data directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Save points to binary file
        points_path = os.path.join(self.base_dir, 'points', f"{terrain.name}.bin")
        os.makedirs(os.path.dirname(points_path), exist_ok=True)
        
        # Save points using array-based storage for efficiency
        points_array = terrain.points.get_points_array()
        point_ids = list(terrain.points._id_to_index.keys())
        
        with open(points_path, 'wb') as f:
            # Save number of points
            f.write(struct.pack('Q', len(point_ids)))
            
            # Save point IDs
            for pid in point_ids:
                f.write(struct.pack('Q', pid))
                
            # Save point coordinates as doubles
            points_array.tofile(f)
        
        # Save metadata
        metadata_path = os.path.join(self.base_dir, 'metadata', f"{terrain.name}.json")
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        
        metadata = {
            'name': terrain.name,
            'stats': terrain.get_stats(),
            'created_at': datetime.now().isoformat()
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Update cache
        self._terrain_cache[terrain.name] = terrain
        self._trim_cache()
        
        self.logger.info(f"Saved terrain {terrain.name} with {len(terrain.points)} points")
        
    def load_terrain(self, name: str) -> Optional[TerrainModel]:
        """Load a terrain model from the database."""
        try:
            # Check paths
            points_path = os.path.join(self.base_dir, 'points', f"{name}.bin")
            metadata_path = os.path.join(self.base_dir, 'metadata', f"{name}.json")
            
            if not os.path.exists(points_path) or not os.path.exists(metadata_path):
                logging.error(f"Terrain not found: {name}")
                logging.debug(f"Points path exists: {os.path.exists(points_path)}")
                logging.debug(f"Metadata path exists: {os.path.exists(metadata_path)}")
                return None
                
            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            # Load points
            with open(points_path, 'rb') as f:
                # Read number of points
                num_points = struct.unpack('Q', f.read(8))[0]
                
                # Read point IDs
                point_ids = [struct.unpack('Q', f.read(8))[0] for _ in range(num_points)]
                
                # Read point coordinates
                points_array = np.fromfile(f, dtype=np.float64)
                points_array = points_array.reshape(-1, 3)
                
            # Create terrain model
            terrain = TerrainModel(name)
            
            # Add points efficiently
            for i, (pid, point) in enumerate(zip(point_ids, points_array)):
                terrain.points._id_to_index[pid] = i
                terrain.points._coordinates.extend([point[0], point[1], point[2]])
                
            # Update stats from metadata
            terrain._stats.update(metadata['stats'])
            
            logging.info(f"Successfully loaded terrain: {name} with {num_points} points")
            return terrain
            
        except Exception as e:
            logging.error(f"Error loading terrain {name}: {str(e)}", exc_info=True)
            return None

    def delete_terrain(self, name: str) -> bool:
        """Delete terrain model and its associated files."""
        try:
            # Remove from cache
            self._terrain_cache.pop(name, None)
            
            # Delete files
            points_path = os.path.join(self.base_dir, 'points', f"{name}.bin")
            metadata_path = os.path.join(self.base_dir, 'metadata', f"{name}.json")
            
            deleted = False
            if os.path.exists(points_path):
                os.remove(points_path)
                deleted = True
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                deleted = True
            
            if deleted:
                self.logger.info(f"Deleted terrain {name}")
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete terrain {name}: {str(e)}")
            return False

    def list_terrains(self) -> List[str]:
        """List all available terrain models."""
        try:
            # List all JSON metadata files
            metadata_dir = os.path.join(self.base_dir, 'metadata')
            if not os.path.exists(metadata_dir):
                return []
                
            terrain_names = []
            for filename in os.listdir(metadata_dir):
                if filename.endswith('.json'):
                    terrain_names.append(filename[:-5])  # Remove .json extension
            
            return sorted(terrain_names)
            
        except Exception as e:
            self.logger.error(f"Failed to list terrains: {str(e)}")
            return []

    def _trim_cache(self) -> None:
        """Remove oldest items from cache if it exceeds maximum size."""
        if len(self._terrain_cache) > self._max_cache_size:
            # Remove oldest entries
            remove_count = len(self._terrain_cache) - self._max_cache_size
            for name in list(self._terrain_cache.keys())[:remove_count]:
                del self._terrain_cache[name]
