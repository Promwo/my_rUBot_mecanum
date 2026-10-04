#!/usr/bin/env python3
"""Plot robot sampling positions coloured by average eCO2."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(description='Plot ENS160 sampling waypoints from a CSV log.')
    parser.add_argument('--csv', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--point-size', type=float, default=20.0)
    parser.add_argument(
        '--standard-axes',
        action='store_true',
        help='Use Pose_X horizontally and Pose_Y vertically. Without this flag, preserve Valeria\'s original swapped-axis view.',
    )
    parser.add_argument('--no-show', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    df = pd.read_csv(args.csv.expanduser())
    required = {'Pose_X', 'Pose_Y', 'eCO2'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'CSV is missing required columns: {sorted(missing)}')

    grouped = df.dropna(subset=['Pose_X', 'Pose_Y', 'eCO2']).groupby(['Pose_X', 'Pose_Y'])['eCO2'].mean().reset_index()
    if grouped.empty:
        raise ValueError('CSV contains no valid pose/eCO2 samples')

    if args.standard_axes:
        x_coords = grouped['Pose_X'].to_numpy()
        y_coords = grouped['Pose_Y'].to_numpy()
        xlabel, ylabel = 'Pose X (meters)', 'Pose Y (meters)'
    else:
        # Preserve the orientation used by Valeria's original script.
        x_coords = grouped['Pose_Y'].to_numpy()
        y_coords = grouped['Pose_X'].to_numpy()
        xlabel, ylabel = 'Pose Y (meters)', 'Pose X (meters)'

    fig, ax = plt.subplots(figsize=(10, 8))
    scatter = ax.scatter(
        x_coords,
        y_coords,
        c=grouped['eCO2'].to_numpy(),
        cmap='rainbow',
        s=args.point_size,
        alpha=0.8,
        label='Trajectory Points',
    )
    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label('Average eCO2 Level (PPM)', fontsize=12)
    ax.set_title('Robot Trajectory Colored by Average eCO2')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, linestyle=':')
    ax.axis('equal')
    fig.tight_layout()

    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=160, bbox_inches='tight')
        print(f'Saved plot to: {output}')

    if not args.no_show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == '__main__':
    main()
