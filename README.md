# Blender GLB Six Views

A tool to render six standard views of 3D GLB models using Blender and combine them into a single image.

## Features

- Renders six standard views (front, left, back, right, top, bottom) of a GLB model
- Combines the views into a single image with labels
- Supports batch processing of multiple GLB files
- Customizable resolution

## New! Eight Views Version

We've added a new version that renders eight views instead of six:
- The original six standard views (front, left, back, right, top, bottom)
- An isometric view without materials (showing the model's geometry)
- A UV map view (showing the model's texture mapping)

The eight views are arranged in a 4x2 grid:
```
1(正面)  2(左视图)  3(背面)  4(等轴测无材质)
5(俯视图) 6(底视图)  7(右视图) 8(UV贴图)
```

## Requirements

- Blender (must be in your PATH)
- Python 3.6+
- PIL (Pillow)

## Usage

### Six Views Version

#### Single Model Processing

```bash
python glb_six_views_main.py path/to/model.glb [--output OUTPUT] [--resolution RESOLUTION] [--keep-temp]
```

#### Batch Processing

```bash
python glb_six_views_batch.py path/to/directory [--output-dir OUTPUT_DIR] [--resolution RESOLUTION] [--keep-temp]
```

### Eight Views Version

#### Single Model Processing

```bash
python glb_eight_views_main.py path/to/model.glb [--output OUTPUT] [--resolution RESOLUTION] [--keep-temp]
```

#### Batch Processing

```bash
python glb_eight_views_batch.py path/to/directory [--output-dir OUTPUT_DIR] [--resolution RESOLUTION] [--keep-temp]
```

## Files

### Six Views Version
- `blender_six_views.py` - Blender script for rendering the six views
- `glb_six_views_main.py` - Main script for processing a single model
- `glb_six_views_batch.py` - Script for batch processing multiple models

### Eight Views Version
- `blender_eight_views.py` - Blender script for rendering the eight views
- `glb_eight_views_main.py` - Main script for processing a single model
- `glb_eight_views_batch.py` - Script for batch processing multiple models

## License

MIT
