#!/usr/bin/env python3
"""Generate Valeria-style eCO2 heatmaps using inverse-distance weighting (IDW)."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import yaml


def parse_args():
    parser = argparse.ArgumentParser(
        description='Overlay an IDW eCO2 map and robot path on a ROS occupancy map.'
    )
    parser.add_argument('--csv', required=True, type=Path, help='Sensor CSV containing Pose_X, Pose_Y and eCO2')
    parser.add_argument('--map', dest='yaml_path', required=True, type=Path, help='ROS map YAML file')
    parser.add_argument('--output', type=Path, help='Optional PNG/PDF output path')
    parser.add_argument('--square-size', type=float, default=0.3, help='IDW grid cell size in metres (default: 0.3)')
    parser.add_argument('--eco2-min', type=float, default=400.0, help='Lower eCO2 clamp in ppm')
    parser.add_argument('--eco2-max', type=float, default=1200.0, help='Upper eCO2 clamp in ppm')
    parser.add_argument('--max-path-gap', type=float, default=0.3, help='Do not connect path points farther apart than this (m)')
    parser.add_argument('--no-show', action='store_true', help='Do not open an interactive matplotlib window')
    return parser.parse_args()


def require_columns(df, columns):
    missing = [name for name in columns if name not in df.columns]
    if missing:
        raise ValueError(f'CSV is missing required columns: {missing}')


def load_map(yaml_path):
    yaml_path = yaml_path.expanduser().resolve()
    with yaml_path.open() as stream:
        map_yaml = yaml.safe_load(stream)

    image_path = Path(map_yaml['image'])
    if not image_path.is_absolute():
        image_path = yaml_path.parent / image_path
    image_path = image_path.resolve()

    img = Image.open(image_path).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    width_px, height_px = img.size
    resolution = float(map_yaml['resolution'])
    origin_x, origin_y, _ = map_yaml['origin']

    bounds = (
        float(origin_x),
        float(origin_x) + width_px * resolution,
        float(origin_y),
        float(origin_y) + height_px * resolution,
    )
    return img, bounds


def main():
    args = parse_args()
    csv_path = args.csv.expanduser().resolve()

    if args.square_size <= 0:
        raise ValueError('--square-size must be greater than zero')
    if args.eco2_max <= args.eco2_min:
        raise ValueError('--eco2-max must be greater than --eco2-min')

    df = pd.read_csv(csv_path)
    require_columns(df, ['Pose_X', 'Pose_Y', 'eCO2'])
    df = df.dropna(subset=['Pose_X', 'Pose_Y', 'eCO2'])
    if df.empty:
        raise ValueError('CSV contains no valid Pose_X/Pose_Y/eCO2 samples')

    # Valeria's processing: average eCO2 across channels at each sampled pose.
    grouped = df.groupby(['Pose_X', 'Pose_Y'])['eCO2'].mean().reset_index()
    x_data = grouped['Pose_X'].to_numpy(dtype=float)
    y_data = grouped['Pose_Y'].to_numpy(dtype=float)
    co2_data = grouped['eCO2'].clip(args.eco2_min, args.eco2_max).to_numpy(dtype=float)

    img, (x_min, x_max, y_min, y_max) = load_map(args.yaml_path)
    print(f'Map bounds (meters): x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]')
    print(f'Using {len(grouped)} unique robot positions from {csv_path}')

    x_bins = np.arange(x_min, x_max, args.square_size)
    y_bins = np.arange(y_min, y_max, args.square_size)
    xx, yy = np.meshgrid(x_bins + args.square_size / 2, y_bins + args.square_size / 2)
    co2_grid = np.zeros(xx.shape, dtype=float)

    grid_points = np.column_stack([xx.ravel(), yy.ravel()])
    sensor_points = np.column_stack([x_data, y_data])

    # Same inverse-distance-squared interpolation used in Valeria's script.
    flat_grid = co2_grid.ravel()
    for index, grid_point in enumerate(grid_points):
        distances = np.linalg.norm(sensor_points - grid_point, axis=1)
        weights = 1.0 / (distances ** 2 + 1e-6)
        flat_grid[index] = np.sum(weights * co2_data) / np.sum(weights)

    fig, ax = plt.subplots(figsize=(13, 13))
    extent = [x_min, x_max, y_min, y_max]
    ax.imshow(np.asarray(img), origin='lower', extent=extent, cmap='gray', alpha=0.3)
    heatmap = ax.imshow(
        co2_grid,
        origin='lower',
        extent=extent,
        cmap='jet',
        interpolation='nearest',
        alpha=0.7,
        vmin=args.eco2_min,
        vmax=args.eco2_max,
        aspect='equal',
    )
    colorbar = fig.colorbar(heatmap, ax=ax, fraction=0.03)
    colorbar.set_label('eCO₂ (ppm)')

    previous_x = previous_y = None
    for x_value, y_value in zip(x_data, y_data):
        if previous_x is not None and np.hypot(x_value - previous_x, y_value - previous_y) < args.max_path_gap:
            ax.plot([previous_x, x_value], [previous_y, y_value], color='black', linewidth=2)
        previous_x, previous_y = x_value, y_value

    ax.set_title('eCO₂ Map with Robot Path')
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    ax.grid(False)
    fig.tight_layout()

    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=160, bbox_inches='tight')
        print(f'Saved map to: {output}')

    if not args.no_show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == '__main__':
    main()
