# Blender GLB Six Views

A tool to render six standard views of 3D GLB models using Blender and combine them into a single image.

## Features

- Renders six standard views (front, left, back, right, top, bottom) of a GLB model
- Combines the views into a single image with labels
- Supports batch processing of multiple GLB files
- Customizable resolution

## Requirements

- Blender (must be in your PATH)
- Python 3.6+
- PIL (Pillow)

## Usage

### Single Model Processing

```bash
python glb_six_views_main.py path/to/model.glb [--output OUTPUT] [--resolution RESOLUTION] [--keep-temp]
```

### Batch Processing

```bash
python glb_six_views_batch.py path/to/directory [--output-dir OUTPUT_DIR] [--resolution RESOLUTION] [--keep-temp]
```

## Files

- `blender_six_views.py` - Blender script for rendering the six views
- `glb_six_views_main.py` - Main script for processing a single model
- `glb_six_views_batch.py` - Script for batch processing multiple models

## License

MIT
