from dxf_importer import DXFPointExtractor
from terrain_interpolation import TerrainInterpolator
from terrain_analysis import TerrainAnalyzer
import os
import time
import psutil
import numpy as np

def format_size(size_bytes):
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} GB"

def test_dxf_processing():
    try:
        print("\nTesting DXF Point Cloud Processing")
        print("-" * 50)
        
        # Process memory before
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        start_time = time.time()
        
        # Initialize extractor
        dxf_file = "data/plan-masse.dxf"
        print(f"\nProcessing DXF file: {dxf_file}")
        extractor = DXFPointExtractor(dxf_file)
        
        # Process and analyze original data
        terrain, stats = extractor.process_and_analyze(
            layer_name="z value TN",
            precision=0.01
        )
        
        # Create interpolator
        print("\nPerforming terrain interpolation...")
        interpolator = TerrainInterpolator(terrain)
        
        # Get optimal resolution
        resolution = interpolator.estimate_optimal_resolution()
        print(f"Estimated optimal grid resolution: {resolution:.2f}m")
        
        # Create dense point cloud
        dense_points = interpolator.create_dense_grid(
            resolution=resolution,
            method='cubic'
        )
        
        print(f"Generated {len(dense_points):,} interpolated points")
        
        # Create new terrain with interpolated points
        dense_terrain = extractor.create_terrain(dense_points)
        
        # Save both terrains
        terrain.save_to_hdf5("terrain_original.h5")
        dense_terrain.save_to_hdf5("terrain_interpolated.h5")
        
        # Analyze dense terrain
        dense_analyzer = TerrainAnalyzer(dense_terrain)
        dense_stats = {
            'point_cloud': extractor.analyze_point_cloud(dense_points),
            'terrain_features': dense_analyzer.analyze_terrain_features()
        }
        
        # Calculate accuracy metrics
        accuracy = interpolator.calculate_accuracy_metrics(dense_points)
        
        # Calculate processing time and memory
        processing_time = time.time() - start_time
        memory_after = process.memory_info().rss
        memory_used = memory_after - memory_before
        
        # Get output file sizes
        orig_size = os.path.getsize("terrain_original.h5")
        interp_size = os.path.getsize("terrain_interpolated.h5")
        
        # Print results
        print("\nProcessing Statistics:")
        print(f"Total processing time: {processing_time:.2f} seconds")
        print(f"Memory used: {format_size(memory_used)}")
        print(f"Original data size: {format_size(orig_size)}")
        print(f"Interpolated data size: {format_size(interp_size)}")
        
        print("\nOriginal Point Cloud Statistics:")
        point_stats = stats['point_cloud']
        print(f"Number of points: {point_stats['num_points']:,}")
        print(f"Point density: {point_stats['point_density']:.2f} points/m²")
        print("\nBounds:")
        for axis in ['x', 'y', 'z']:
            min_val, max_val = point_stats['bounds'][axis]
            print(f"{axis.upper()}: {min_val:.2f} to {max_val:.2f}")
        
        print("\nInterpolated Point Cloud Statistics:")
        dense_point_stats = dense_stats['point_cloud']
        print(f"Number of points: {dense_point_stats['num_points']:,}")
        print(f"Point density: {dense_point_stats['point_density']:.2f} points/m²")
        
        if accuracy:
            print("\nInterpolation Accuracy:")
            print(f"Mean absolute error: {accuracy['mean_absolute_error']:.3f}m")
            print(f"Max absolute error: {accuracy['max_absolute_error']:.3f}m")
            print(f"RMSE: {accuracy['rmse']:.3f}m")
            print(f"Mean XY distance: {accuracy['mean_xy_distance']:.3f}m")
            print(f"Test points used: {accuracy['test_points']}")
        
        print("\nOriginal Terrain Features:")
        terrain_stats = stats['terrain_features']
        print(f"Mean slope: {terrain_stats['mean_slope']:.2f}°")
        print(f"Max slope: {terrain_stats['max_slope']:.2f}°")
        print(f"Mean roughness: {terrain_stats['mean_roughness']:.3f}")
        print(f"Surface area: {terrain_stats['area_3d']:.2f} m²")
        print(f"Projected area: {terrain_stats['area_2d']:.2f} m²")
        print(f"Volume above base: {terrain_stats['volume']:.2f} m³")
        print(f"Terrain complexity: {terrain_stats['terrain_complexity']:.2f}")
        
        print("\nInterpolated Terrain Features:")
        dense_terrain_stats = dense_stats['terrain_features']
        print(f"Mean slope: {dense_terrain_stats['mean_slope']:.2f}°")
        print(f"Max slope: {dense_terrain_stats['max_slope']:.2f}°")
        print(f"Mean roughness: {dense_terrain_stats['mean_roughness']:.3f}")
        print(f"Surface area: {dense_terrain_stats['area_3d']:.2f} m²")
        print(f"Projected area: {dense_terrain_stats['area_2d']:.2f} m²")
        print(f"Volume above base: {dense_terrain_stats['volume']:.2f} m³")
        print(f"Terrain complexity: {dense_terrain_stats['terrain_complexity']:.2f}")
        
    except Exception as e:
        print(f"\nError during processing: {str(e)}")
        raise
    finally:
        # Clean up
        for file in ["terrain_original.h5", "terrain_interpolated.h5"]:
            if os.path.exists(file):
                os.remove(file)

if __name__ == "__main__":
    test_dxf_processing()
