#!/usr/bin/env python3
"""Generate an IDW eCO2 heatmap for one ENS160 channel or all channels."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import yaml


def parse_args():
    parser = argparse.ArgumentParser(description='Plot a Valeria-style eCO2 IDW map by sensor channel.')
    parser.add_argument('--csv', required=True, type=Path)
    parser.add_argument('--map', dest='yaml_path', required=True, type=Path)
    parser.add_argument('--channel', default='all', help='Sensor channel number (0-5) or "all"')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--square-size', type=float, default=0.3)
    parser.add_argument('--eco2-min', type=float, default=400.0)
    parser.add_argument('--eco2-max', type=float, default=1200.0)
    parser.add_argument('--no-show', action='store_true')
    return parser.parse_args()


def load_map(yaml_path):
    yaml_path = yaml_path.expanduser().resolve()
    with yaml_path.open() as stream:
        metadata = yaml.safe_load(stream)
    image_path = Path(metadata['image'])
    if not image_path.is_absolute():
        image_path = yaml_path.parent / image_path
    image = Image.open(image_path).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    width, height = image.size
    resolution = float(metadata['resolution'])
    origin_x, origin_y, _ = metadata['origin']
    return image, (origin_x, origin_x + width * resolution, origin_y, origin_y + height * resolution)


def main():
    args = parse_args()
    df = pd.read_csv(args.csv.expanduser())
    required = {'Pose_X', 'Pose_Y', 'eCO2'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'CSV is missing required columns: {sorted(missing)}')

    if args.channel.lower() == 'all':
        filtered = df
        title_suffix = 'average over all channels'
    else:
        if 'Channel' not in df.columns:
            raise ValueError('CSV needs a Channel column when --channel is used')
        channel = int(args.channel)
        filtered = df[df['Channel'] == channel]
        title_suffix = f'Channel {channel}'

    filtered = filtered.dropna(subset=['Pose_X', 'Pose_Y', 'eCO2'])
    if filtered.empty:
        raise ValueError('No samples remain after channel/filter selection')

    grouped = filtered.groupby(['Pose_X', 'Pose_Y'])['eCO2'].mean().reset_index()
    x_data = grouped['Pose_X'].to_numpy(dtype=float)
    y_data = grouped['Pose_Y'].to_numpy(dtype=float)
    co2_data = grouped['eCO2'].clip(args.eco2_min, args.eco2_max).to_numpy(dtype=float)

    image, (x_min, x_max, y_min, y_max) = load_map(args.yaml_path)
    x_bins = np.arange(x_min, x_max, args.square_size)
    y_bins = np.arange(y_min, y_max, args.square_size)
    xx, yy = np.meshgrid(x_bins + args.square_size / 2, y_bins + args.square_size / 2)
    grid = np.zeros(xx.shape, dtype=float)
    sensor_points = np.column_stack([x_data, y_data])

    flat_grid = grid.ravel()
    for index, grid_point in enumerate(np.column_stack([xx.ravel(), yy.ravel()])):
        distances = np.linalg.norm(sensor_points - grid_point, axis=1)
        weights = 1.0 / (distances ** 2 + 1e-6)
        flat_grid[index] = np.sum(weights * co2_data) / np.sum(weights)

    fig, ax = plt.subplots(figsize=(13, 13))
    extent = [x_min, x_max, y_min, y_max]
    ax.imshow(np.asarray(image), origin='lower', extent=extent, cmap='gray', alpha=0.3)
    heatmap = ax.imshow(
        grid,
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
    ax.set_title(f'eCO₂ Map ({title_suffix})')
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
