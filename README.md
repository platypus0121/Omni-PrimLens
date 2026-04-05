# PrimLens

**Version:** 0.1.0
**Extension ID:** `omni.prim.primlens`

---

## Overview

PrimLens is a NVIDIA Omniverse Kit Extension that automatically displays a real-time isolated 3D preview of any Prim selected in the Stage. Only the selected Prim appears in the **PrimLens** viewport — no other objects from the scene are visible.

Key features:
- Listens to Stage selection events and responds instantly when the selection changes
- Isolates the selected Prim in a dedicated viewport, excluding all other scene objects
- Viewport supports mouse orbit and zoom interaction
- Automatically frames the camera to fit the selected Prim

---

## Architecture

```
omni.prim.primlens/
├── extension.py        # Extension lifecycle (on_startup / on_shutdown)
└── preview_widget.py   # Isolated USD Context, Viewport window, and Stage management
```

### Module Responsibilities

| File | Responsibility |
|---|---|
| `extension.py` | Subscribes to `SELECTION_CHANGED` events, initializes `PrimPreviewWidget`, releases resources on shutdown |
| `preview_widget.py` | Manages the `"prim_preview"` USD Context, the PrimLens Viewport window, and the isolated Stage lifecycle |

### Selection Flow

```
User selects a Prim in the Stage panel
        │
        ▼
MyExtension._on_stage_event()        ← triggered by stage_event_stream
        │
        ▼
PrimPreviewWidget.focus_on_prim()
        │
        ├─ main_stage.Flatten()       ← merge all sublayers into one
        ├─ Sdf.CopySpec(src, prim_path, dst, "/Preview")
        │                             ← copy only the selected Prim
        ├─ Add DomeLight + DistantLight
        ├─ dst_layer.Export(temp.usda)
        │
        ▼
preview_context.open_stage_with_callback(temp.usda)
        │
        ▼
frame_viewport_prims(viewport_api, ["/Preview"])
```

## Technical Details

| Technology | Purpose |
|---|---|
| `omni.usd.create_context("prim_preview")` | Creates a USD Context fully isolated from the main scene |
| `omni.kit.viewport.utility.create_viewport_window(usd_context_name=...)` | Binds the Viewport to the isolated Context so the main scene is never visible |
| `pxr.Sdf.CopySpec` | Copies a single Prim spec from the flattened main stage Layer |
| `pxr.UsdLux.DomeLight / DistantLight` | Adds lighting to the isolated Stage to prevent a black viewport |
| `UsdContext.open_stage_with_callback` | Loads the temporary Stage through Kit's full loading pipeline, ensuring all viewport subsystems initialize correctly |
| `stage_event_stream` + `StageEventType.SELECTION_CHANGED` | Listens for selection change events |
| `omni.kit.viewport.utility.frame_viewport_prims` | Frames the camera to fit the specified Prim |

## Usage

### Enabling the Extension

1. Launch the Kit application
2. Open the **Extension Manager** (Window → Extensions)
3. Search for `PrimLens` and click **Enable**

### Previewing a Prim

1. Open or create a USD Stage
2. Click any Prim in the **Stage** panel (e.g. Cube, Sphere, Mesh)
3. The **PrimLens** viewport will automatically show an isolated 3D preview of that Prim
4. Use the mouse to orbit and zoom within the viewport

Demo
<img width="1917" height="1045" alt="demo" src="https://github.com/user-attachments/assets/58aa10bd-f6fa-4cba-a17e-f7dbf331cfdd" />

---

## Dependencies

```toml
[dependencies]
"omni.kit.uiapp" = {}
"omni.kit.viewport.utility" = {}
"omni.usd" = {}
```
