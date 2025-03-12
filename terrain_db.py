import sqlite3
import json
from point3d import Point3D
from datetime import datetime

class TerrainDatabase:
    def __init__(self, db_path='terrain.db'):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create terrain_models table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS terrain_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bounds TEXT,  -- JSON string of bounds
                    point_count INTEGER,
                    stats TEXT    -- JSON string of terrain statistics
                )
            ''')
            
            # Create points table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS points (
                    id INTEGER PRIMARY KEY,
                    terrain_id INTEGER,
                    x REAL,
                    y REAL,
                    z REAL,
                    FOREIGN KEY (terrain_id) REFERENCES terrain_models(id)
                )
            ''')
            
            # Create break_lines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS break_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    terrain_id INTEGER,
                    point_ids TEXT,  -- JSON array of point IDs
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (terrain_id) REFERENCES terrain_models(id)
                )
            ''')
            
            conn.commit()

    def save_terrain(self, name, points, bounds, stats, break_lines=None):
        """Save terrain model with points and break lines."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert terrain model
            cursor.execute('''
                INSERT INTO terrain_models (name, bounds, point_count, stats)
                VALUES (?, ?, ?, ?)
            ''', (name, json.dumps(bounds), len(points), json.dumps(stats)))
            
            terrain_id = cursor.lastrowid
            
            # Insert points
            points_data = [(point.id, terrain_id, point.x, point.y, point.z) for point in points]
            cursor.executemany('''
                INSERT INTO points (id, terrain_id, x, y, z)
                VALUES (?, ?, ?, ?, ?)
            ''', points_data)
            
            # Insert break lines if provided
            if break_lines:
                break_lines_data = [(terrain_id, json.dumps(line)) for line in break_lines]
                cursor.executemany('''
                    INSERT INTO break_lines (terrain_id, point_ids)
                    VALUES (?, ?)
                ''', break_lines_data)
            
            conn.commit()
            return terrain_id

    def load_terrain(self, terrain_id):
        """Load terrain model with points and break lines."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get terrain model
            cursor.execute('SELECT * FROM terrain_models WHERE id = ?', (terrain_id,))
            terrain = cursor.fetchone()
            if not terrain:
                raise ValueError(f"Terrain model {terrain_id} not found")
            
            # Get points
            cursor.execute('SELECT id, x, y, z FROM points WHERE terrain_id = ?', (terrain_id,))
            points = [Point3D(id=row[0], x=row[1], y=row[2], z=row[3]) 
                     for row in cursor.fetchall()]
            
            # Get break lines
            cursor.execute('SELECT point_ids FROM break_lines WHERE terrain_id = ?', (terrain_id,))
            break_lines = [json.loads(row[0]) for row in cursor.fetchall()]
            
            return {
                'terrain': {
                    'id': terrain[0],
                    'name': terrain[1],
                    'created_at': terrain[2],
                    'bounds': json.loads(terrain[3]),
                    'point_count': terrain[4],
                    'stats': json.loads(terrain[5])
                },
                'points': points,
                'break_lines': break_lines
            }

    def list_terrains(self):
        """List all saved terrain models."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, created_at, point_count 
                FROM terrain_models 
                ORDER BY created_at DESC
            ''')
            return cursor.fetchall()

    def delete_terrain(self, terrain_id):
        """Delete a terrain model and its associated data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM break_lines WHERE terrain_id = ?', (terrain_id,))
            cursor.execute('DELETE FROM points WHERE terrain_id = ?', (terrain_id,))
            cursor.execute('DELETE FROM terrain_models WHERE id = ?', (terrain_id,))
            conn.commit()
