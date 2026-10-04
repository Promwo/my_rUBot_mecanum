#!/usr/bin/env python3
"""Print metric bounds for a ROS map YAML + image pair."""

import argparse
from pathlib import Path

from PIL import Image
import yaml


def main():
    parser = argparse.ArgumentParser(description='Compute ROS occupancy-map bounds in metres.')
    parser.add_argument('--map', dest='yaml_path', required=True, type=Path)
    args = parser.parse_args()

    yaml_path = args.yaml_path.expanduser().resolve()
    with yaml_path.open() as stream:
        metadata = yaml.safe_load(stream)

    image_path = Path(metadata['image'])
    if not image_path.is_absolute():
        image_path = yaml_path.parent / image_path
    image_path = image_path.resolve()

    with Image.open(image_path) as image:
        width, height = image.size

    resolution = float(metadata['resolution'])
    origin_x, origin_y, _ = metadata['origin']
    x_max = origin_x + width * resolution
    y_max = origin_y + height * resolution

    print(f'Map image: {image_path}')
    print(f'Map bounds (meters): x=[{origin_x}, {x_max}], y=[{origin_y}, {y_max}]')


if __name__ == '__main__':
    main()
