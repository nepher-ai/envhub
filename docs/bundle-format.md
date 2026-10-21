# Bundle format

An EnvHub bundle is a folder, or a `.zip` of one, with a `manifest.yaml` at its root. Upload it with:

```bash
nepher upload ./my-bundle --category navigation
```

Folders are zipped automatically. Version-control folders, virtualenvs, `__pycache__`, `.pyc` and `.env` files are left out of the archive.

## USD environment

A USD environment ships USD assets together with their scene configuration.

```yaml
id: digital-twin-warehouse-v1
type: usd
version: 1.0.0
category: navigation
description: Digital twin of a small warehouse for navigation training

scenes:
  - scene_id: small_warehouse
    description: Small warehouse with realistic layout and obstacles
    usd: small_warehouse_digital_twin.usd
    omap_meta: digital_twin_omap/map.yaml   # optional ROS occupancy map
    scene: small_warehouse_scene.py         # optional Python scene config
```

The optional scene file configures how the USD assets are used in simulation: transform and scale, terrain friction, lighting and sky, spawn areas and exclusion zones.

When a scene has an occupancy map, the map decides where robots and goals may be placed, and the scene's `spawn_areas` and `exclusion_zones` are not applied. Without a map, each spawn area is sampled separately according to its `weight`. If the map frame doesn't line up with the USD origin, set `occupancy_map_offset = (x, y, yaw)` in the scene config.

## Preset environment

A preset environment generates its scenes programmatically from Python preset files.

```yaml
id: indoor-environments-v1
type: preset
version: 1.0.0
category: navigation
description: Indoor navigation environments

preset_scenes:
  - scene_id: hospital
    description: Hospital corridor environment
    preset: hospital_preset.py
  - scene_id: warehouse
    description: Warehouse with shelves and bounding walls
    preset: warehouse_preset.py
```

## Paths

All paths in the manifest (`usd`, `omap_meta`, `scene`, `preset`) are relative to the bundle root and must stay inside the bundle. Absolute paths and paths that climb out with `..` are rejected. Loaded configs receive absolute paths into the local cache.

## Security

Preset and scene files run as ordinary Python when a scene is loaded or viewed. Only load bundles from authors you trust.
