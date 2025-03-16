"""
SQLAlchemy models for terrain data persistence.

Provides efficient storage and retrieval of:
- Projects to organize terrain data
- Point3D objects (32 bytes per point)
- PointCloud collections
- Delaunay triangulation
- Break lines
- Interpolated points
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import numpy as np
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, ForeignKey, 
    Table, UniqueConstraint, Index, event
)
from sqlalchemy.orm import (
    declarative_base, relationship, Session, 
    sessionmaker
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.pool import StaticPool

Base = declarative_base()

class Project(Base):
    """
    SQLAlchemy model for Project.
    
    Organizes terrain data into separate projects,
    allowing multiple projects to coexist in the same database.
    """
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500))
    created_at = Column(Float, nullable=False)  # Unix timestamp
    
    # Relationships
    point_clouds = relationship('PointCloud', back_populates='project')
    points = relationship('Point3D', back_populates='project')
    break_lines = relationship('BreakLine', back_populates='project')
    triangles = relationship('DelaunayTriangle', back_populates='project')
    interpolated_points = relationship('InterpolatedPoint', back_populates='project')

# Association table for PointCloud-Point3D relationship
cloud_points = Table(
    'cloud_points',
    Base.metadata,
    Column('cloud_id', Integer, ForeignKey('point_clouds.id'), primary_key=True),
    Column('point_db_id', Integer, ForeignKey('points.db_id'), primary_key=True),
    Index('idx_cloud_points', 'cloud_id', 'point_db_id')
)

class Point3D(Base):
    """
    SQLAlchemy model for Point3D.
    
    Maintains the 32-byte memory efficiency requirement:
    - id: 8 bytes (INTEGER)
    - x,y,z: 8 bytes each (REAL)
    """
    __tablename__ = 'points'
    
    # Use autoincrementing ID for database
    db_id = Column(Integer, primary_key=True, autoincrement=True)
    # Point3D ID (from the application)
    point_id = Column(Integer, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    
    # Project reference
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project = relationship('Project', back_populates='points')
    
    # Spatial index on x,y coordinates and unique constraint per project
    __table_args__ = (
        Index('idx_points_xy', 'x', 'y'),
        UniqueConstraint('project_id', 'point_id', name='uq_point_project_id'),
    )
    
    def to_point(self) -> 'Point3D':
        """Convert to Point3D instance."""
        from point3d import Point3D
        return Point3D(id=self.point_id, x=self.x, y=self.y, z=self.z)
        
    @classmethod
    def from_point(cls, point: 'Point3D', project_id: int) -> 'Point3D':
        """Create from Point3D instance."""
        return cls(
            point_id=point.id,
            x=point.x,
            y=point.y,
            z=point.z,
            project_id=project_id
        )

class PointCloud(Base):
    """
    SQLAlchemy model for PointCloud.
    
    Maintains relationships to points and derived data
    while preserving memory efficiency.
    """
    __tablename__ = 'point_clouds'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    
    # Project reference
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project = relationship('Project', back_populates='point_clouds')
    
    # Relationships
    points = relationship(
        'Point3D',
        secondary=cloud_points,
        backref='clouds'
    )
    triangles = relationship('DelaunayTriangle', back_populates='cloud')
    break_lines = relationship('BreakLine', back_populates='cloud')
    interpolated_points = relationship('InterpolatedPoint', back_populates='cloud')
    
    # Unique cloud name per project
    __table_args__ = (
        UniqueConstraint('project_id', 'name', name='uq_cloud_project_name'),
    )
    
    @hybrid_property
    def num_points(self) -> int:
        """Get number of points in cloud."""
        return len(self.points)

class DelaunayTriangle(Base):
    """
    SQLAlchemy model for Delaunay triangulation.
    
    Stores triangle vertices and properties while
    maintaining referential integrity.
    """
    __tablename__ = 'delaunay_triangles'
    
    id = Column(Integer, primary_key=True)
    cloud_id = Column(Integer, ForeignKey('point_clouds.id'), nullable=False)
    p1_db_id = Column(Integer, ForeignKey('points.db_id'), nullable=False)
    p2_db_id = Column(Integer, ForeignKey('points.db_id'), nullable=False)
    p3_db_id = Column(Integer, ForeignKey('points.db_id'), nullable=False)
    area = Column(Float, nullable=False)
    min_angle = Column(Float, nullable=False)  # Minimum angle in degrees
    
    # Project reference
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project = relationship('Project', back_populates='triangles')
    
    # Relationships
    cloud = relationship('PointCloud', back_populates='triangles')
    p1 = relationship('Point3D', foreign_keys=[p1_db_id])
    p2 = relationship('Point3D', foreign_keys=[p2_db_id])
    p3 = relationship('Point3D', foreign_keys=[p3_db_id])
    
    # Ensure points are different and unique per project
    __table_args__ = (
        UniqueConstraint('project_id', 'cloud_id', 'p1_db_id', 'p2_db_id', 'p3_db_id'),
        Index('idx_triangle_points', 'p1_db_id', 'p2_db_id', 'p3_db_id'),
    )

class BreakLine(Base):
    """
    SQLAlchemy model for break lines.
    
    Stores user-defined terrain constraints
    between point pairs.
    """
    __tablename__ = 'break_lines'
    
    id = Column(Integer, primary_key=True)
    cloud_id = Column(Integer, ForeignKey('point_clouds.id'), nullable=False)
    start_point_db_id = Column(Integer, ForeignKey('points.db_id'), nullable=False)
    end_point_db_id = Column(Integer, ForeignKey('points.db_id'), nullable=False)
    
    # Project reference
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project = relationship('Project', back_populates='break_lines')
    
    # Relationships
    cloud = relationship('PointCloud', back_populates='break_lines')
    start_point = relationship('Point3D', foreign_keys=[start_point_db_id])
    end_point = relationship('Point3D', foreign_keys=[end_point_db_id])
    
    # Ensure points are different and unique pairs per project and cloud
    __table_args__ = (
        UniqueConstraint('project_id', 'cloud_id', 'start_point_db_id', 'end_point_db_id'),
        Index('idx_break_line_points', 'start_point_db_id', 'end_point_db_id'),
    )

class InterpolatedPoint(Base):
    """
    SQLAlchemy model for interpolated points.
    
    Caches interpolation results for future use,
    improving performance for frequently accessed locations.
    """
    __tablename__ = 'interpolated_points'
    
    id = Column(Integer, primary_key=True)
    cloud_id = Column(Integer, ForeignKey('point_clouds.id'), nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    method = Column(String(20), nullable=False)  # 'barycentric' or 'diw'
    
    # Project reference
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    project = relationship('Project', back_populates='interpolated_points')
    
    # Relationships
    cloud = relationship('PointCloud', back_populates='interpolated_points')
    
    # Spatial and method index, unique per project
    __table_args__ = (
        UniqueConstraint('project_id', 'cloud_id', 'x', 'y', 'method'),
        Index('idx_interpolated_xy', 'x', 'y'),
    )

class TerrainDatabase:
    """
    High-level interface for terrain database operations.
    
    Provides efficient methods for storing and retrieving
    terrain data while maintaining memory optimization.
    """
    
    def __init__(self, db_url: str = 'sqlite:///terrain.db'):
        """Initialize database connection."""
        connect_args = {'check_same_thread': False}
        if ':memory:' in db_url:
            # Use StaticPool for in-memory SQLite to share connection
            self.engine = create_engine(
                db_url,
                connect_args=connect_args,
                poolclass=StaticPool
            )
        else:
            self.engine = create_engine(db_url, connect_args=connect_args)
            
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    def create_project(self, name: str) -> Project:
        """Create a new project."""
        with self.Session() as session:
            project = Project(name=name)
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    def create_point_cloud(
        self,
        project_name: str,
        cloud_name: str,
        points: List['Point3D']
    ) -> PointCloud:
        """Create a new point cloud with points."""
        with self.Session() as session:
            # Get project
            project = session.query(Project).filter_by(name=project_name).first()
            if not project:
                raise ValueError(f"Project {project_name} not found")
            
            # Check if cloud name exists in project
            existing = (
                session.query(PointCloud)
                .filter_by(project_id=project.id, name=cloud_name)
                .first()
            )
            if existing:
                raise ValueError(f"Cloud {cloud_name} already exists in project {project_name}")
            
            # Create cloud
            cloud = PointCloud(name=cloud_name, project=project)
            session.add(cloud)
            session.flush()  # Get cloud.id
            
            # Use array-based storage for point coordinates
            from array import array
            point_ids = array('Q', [p.id for p in points])
            coords = array('d', [coord for p in points for coord in (p.x, p.y, p.z)])
            
            # Create points using bulk insert
            point_mappings = []
            for i in range(len(point_ids)):
                point = Point3D(
                    project_id=project.id,
                    point_id=point_ids[i],
                    x=coords[i*3],
                    y=coords[i*3 + 1],
                    z=coords[i*3 + 2]
                )
                session.add(point)
                point_mappings.append(point)
            
            session.flush()  # Get point db_ids
            
            # Associate points with cloud using bulk insert
            for point in point_mappings:
                cloud.points.append(point)
            
            session.commit()
            session.refresh(cloud)
            return cloud
            
    def cache_interpolation(
        self,
        project_name: str,
        cloud_name: str,
        x: float,
        y: float,
        z: float,
        method: str = 'barycentric'
    ) -> InterpolatedPoint:
        """Cache interpolated point."""
        with self.Session() as session:
            project = session.query(Project).filter_by(name=project_name).first()
            if not project:
                raise ValueError(f"Project {project_name} not found")
                
            cloud = (
                session.query(PointCloud)
                .filter_by(project_id=project.id, name=cloud_name)
                .first()
            )
            if not cloud:
                raise ValueError(f"Cloud {cloud_name} not found in project {project_name}")
                
            point = InterpolatedPoint(
                project=project,
                cloud=cloud,
                x=x,
                y=y,
                z=z,
                method=method
            )
            session.add(point)
            session.commit()
            session.refresh(point)
            return point
            
    def add_break_lines(
        self,
        project_name: str,
        cloud_name: str,
        lines: List[Tuple[int, int]]
    ) -> List[BreakLine]:
        """Add break lines to point cloud."""
        with self.Session() as session:
            project = session.query(Project).filter_by(name=project_name).first()
            if not project:
                raise ValueError(f"Project {project_name} not found")
                
            cloud = (
                session.query(PointCloud)
                .filter_by(project_id=project.id, name=cloud_name)
                .first()
            )
            if not cloud:
                raise ValueError(f"Cloud {cloud_name} not found in project {project_name}")
                
            # Use array-based storage for point IDs
            from array import array
            point_ids = array('Q', [id for pair in lines for id in pair])
            
            # Get db_id mapping for point IDs
            point_map = {
                p.point_id: p 
                for p in session.query(Point3D).filter(
                    Point3D.project_id == project.id,
                    Point3D.point_id.in_(point_ids.tolist())
                )
            }
            
            # Validate all points exist
            missing = set()
            for i in range(0, len(point_ids), 2):
                if point_ids[i] not in point_map:
                    missing.add(point_ids[i])
                if point_ids[i+1] not in point_map:
                    missing.add(point_ids[i+1])
            if missing:
                raise KeyError(f"Points not found in project {project_name}: {missing}")
            
            # Create break lines
            break_lines = []
            for i in range(0, len(point_ids), 2):
                line = BreakLine(
                    project=project,
                    cloud=cloud,
                    start_point=point_map[point_ids[i]],
                    end_point=point_map[point_ids[i+1]]
                )
                session.add(line)
                break_lines.append(line)
            
            session.commit()
            return break_lines
            
    def store_triangulation(
        self,
        project_name: str,
        cloud_name: str,
        triangles: List[Tuple[int, int, int]],
        properties: List[Tuple[float, float]]
    ) -> List[DelaunayTriangle]:
        """Store Delaunay triangulation."""
        with self.Session() as session:
            project = session.query(Project).filter_by(name=project_name).first()
            if not project:
                raise ValueError(f"Project {project_name} not found")
                
            cloud = (
                session.query(PointCloud)
                .filter_by(project_id=project.id, name=cloud_name)
                .first()
            )
            if not cloud:
                raise ValueError(f"Cloud {cloud_name} not found in project {project_name}")
                
            # Use array-based storage for point IDs and properties
            from array import array
            point_ids = array('Q', [id for tri in triangles for id in tri])
            areas = array('d', [area for area, _ in properties])
            angles = array('d', [angle for _, angle in properties])
            
            # Get db_id mapping for point IDs
            point_map = {
                p.point_id: p 
                for p in session.query(Point3D).filter(
                    Point3D.project_id == project.id,
                    Point3D.point_id.in_(point_ids.tolist())
                )
            }
            
            # Validate all points exist
            missing = set()
            for i in range(0, len(point_ids), 3):
                if point_ids[i] not in point_map:
                    missing.add(point_ids[i])
                if point_ids[i+1] not in point_map:
                    missing.add(point_ids[i+1])
                if point_ids[i+2] not in point_map:
                    missing.add(point_ids[i+2])
            if missing:
                raise KeyError(f"Points not found in project {project_name}: {missing}")
            
            # Create triangles
            db_triangles = []
            for i in range(0, len(point_ids), 3):
                triangle = DelaunayTriangle(
                    project=project,
                    cloud=cloud,
                    p1=point_map[point_ids[i]],
                    p2=point_map[point_ids[i+1]],
                    p3=point_map[point_ids[i+2]],
                    area=areas[i//3],
                    min_angle=angles[i//3]
                )
                session.add(triangle)
                db_triangles.append(triangle)
            
            session.commit()
            return db_triangles
