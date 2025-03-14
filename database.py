from __future__ import annotations
import os
import json
import logging
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
        """
        Save terrain model using binary format for points and JSON for metadata.
        Points are stored separately from metadata for memory efficiency.
        """
        try:
            # Save points in binary format
            points_path = os.path.join(self.base_dir, 'points', f'{terrain.name}.bin')
            with open(points_path, 'wb') as f:
                f.write(terrain.points.to_bytes())
            
            # Save metadata (everything except points) as JSON
            metadata = {
                'name': terrain.name,
                'stats': terrain.get_stats(),
                'break_lines': terrain._break_lines
            }
            
            metadata_path = os.path.join(self.base_dir, 'metadata', f'{terrain.name}.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update cache
            self._terrain_cache[terrain.name] = terrain
            self._trim_cache()
            
            self.logger.info(f"Saved terrain {terrain.name} with {len(terrain.points)} points")
            
        except Exception as e:
            self.logger.error(f"Failed to save terrain {terrain.name}: {str(e)}")
            raise

    def load_terrain(self, name: str) -> Optional[TerrainModel]:
        """
        Load terrain model from storage.
        Uses caching to avoid reloading frequently accessed terrains.
        """
        try:
            # Check cache first
            if name in self._terrain_cache:
                self.logger.debug(f"Cache hit for terrain {name}")
                return self._terrain_cache[name]
            
            # Load metadata
            metadata_path = os.path.join(self.base_dir, 'metadata', f'{name}.json')
            if not os.path.exists(metadata_path):
                return None
                
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Create terrain model
            terrain = TerrainModel(name)
            
            # Load points from binary file
            points_path = os.path.join(self.base_dir, 'points', f'{name}.bin')
            if os.path.exists(points_path):
                with open(points_path, 'rb') as f:
                    terrain.points = PointCloud.from_bytes(f.read())
            
            # Add break lines
            for break_line in metadata.get('break_lines', []):
                terrain.add_break_line(break_line)
            
            # Update cache
            self._terrain_cache[name] = terrain
            self._trim_cache()
            
            self.logger.info(f"Loaded terrain {name} with {len(terrain.points)} points")
            return terrain
            
        except Exception as e:
            self.logger.error(f"Failed to load terrain {name}: {str(e)}")
            return None

    def delete_terrain(self, name: str) -> bool:
        """Delete terrain model and its associated files."""
        try:
            # Remove from cache
            self._terrain_cache.pop(name, None)
            
            # Delete files
            points_path = os.path.join(self.base_dir, 'points', f'{name}.bin')
            metadata_path = os.path.join(self.base_dir, 'metadata', f'{name}.json')
            
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
