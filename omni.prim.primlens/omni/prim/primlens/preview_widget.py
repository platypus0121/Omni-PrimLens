# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

import os
import tempfile
import carb
import omni.usd

_PREVIEW_ROOT = "/Preview"
_CONTEXT_NAME = "prim_preview"


class PrimPreviewWidget:
    """Isolated 3D Prim Preview viewport.

    Architecture:
    - Creates a named USD context ("prim_preview") separate from the main scene.
    - Viewport window is bound to that context, so it never sees the main stage.
    - On focus_on_prim(): builds a fresh in-memory stage with only the selected
      prim + lights, exports it to a temp .usda file, then opens it via
      open_stage_with_callback (the reliable Kit code path for stage loading).
    """

    WINDOW_NAME = "PrimLens"
    WIDTH = 360
    HEIGHT = 300

    def __init__(self):
        self._viewport_window = None
        self._preview_context: omni.usd.UsdContext | None = None
        # Reuse the same temp file path each time (overwrite on every selection)
        self._temp_path = os.path.join(
            tempfile.gettempdir(), "omni_primlens_preview.usda"
        )
        self._setup()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def focus_on_prim(self, prim_path: str) -> None:
        """Show only *prim_path* in the isolated preview viewport."""
        if not prim_path or not self._viewport_window or not self._preview_context:
            return
        try:
            self._load_isolated_prim(prim_path)
        except Exception as exc:
            carb.log_warn(f"[PrimPreviewWidget] focus_on_prim failed: {exc}")

    def destroy(self) -> None:
        """Release viewport, USD context, and temp file."""
        if self._viewport_window is not None:
            try:
                self._viewport_window.destroy()
            except Exception as exc:
                carb.log_warn(f"[PrimPreviewWidget] viewport destroy: {exc}")
            finally:
                self._viewport_window = None

        try:
            omni.usd.destroy_context(_CONTEXT_NAME)
        except Exception as exc:
            carb.log_warn(f"[PrimPreviewWidget] context destroy: {exc}")
        self._preview_context = None

        try:
            if os.path.exists(self._temp_path):
                os.unlink(self._temp_path)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        try:
            self._preview_context = omni.usd.create_context(_CONTEXT_NAME)

            from omni.kit.viewport.utility import create_viewport_window

            self._viewport_window = create_viewport_window(
                name=self.WINDOW_NAME,
                usd_context_name=_CONTEXT_NAME,
                width=self.WIDTH,
                height=self.HEIGHT,
            )
        except Exception as exc:
            carb.log_warn(f"[PrimPreviewWidget] setup failed: {exc}")

    def _load_isolated_prim(self, prim_path: str) -> None:
        """Build an isolated stage with only *prim_path* + lights, open it."""
        from pxr import Usd, Sdf, UsdLux, UsdGeom, Gf

        main_stage = omni.usd.get_context().get_stage()
        if not main_stage:
            carb.log_warn("[PrimPreviewWidget] No main stage open")
            return

        # Flatten so prims defined in any sublayer are captured
        src_layer = main_stage.Flatten()

        # ── Build isolated stage ───────────────────────────────────────
        preview_stage = Usd.Stage.CreateInMemory()
        dst_layer = preview_stage.GetRootLayer()

        Sdf.CopySpec(src_layer, Sdf.Path(prim_path), dst_layer, Sdf.Path(_PREVIEW_ROOT))

        # ── Lighting ──────────────────────────────────────────────────
        dome = UsdLux.DomeLight.Define(preview_stage, "/PreviewDomeLight")
        dome.GetIntensityAttr().Set(500.0)
        dome.GetColorAttr().Set(Gf.Vec3f(1.0, 1.0, 1.0))

        distant = UsdLux.DistantLight.Define(preview_stage, "/PreviewDistantLight")
        distant.GetIntensityAttr().Set(2000.0)
        distant.GetAngleAttr().Set(0.53)
        UsdGeom.Xformable(distant).AddRotateXYZOp().Set(Gf.Vec3f(-45.0, 45.0, 0.0))

        # ── Default prim ──────────────────────────────────────────────
        root_prim = preview_stage.GetPrimAtPath(_PREVIEW_ROOT)
        if root_prim:
            preview_stage.SetDefaultPrim(root_prim)

        # ── Export → temp file → open via Kit API ─────────────────────
        # open_stage_with_callback is the reliable code path in Kit.
        # attach_stage_with_callback(Usd.Stage) is unreliable for in-memory stages
        # and causes "Invalid UsdStage" errors in viewport raycast code.
        dst_layer.Export(self._temp_path)

        def _on_opened(result, error):
            if result:
                self._frame(_PREVIEW_ROOT)
            elif error:
                carb.log_warn(f"[PrimPreviewWidget] open_stage failed: {error}")

        self._preview_context.open_stage_with_callback(self._temp_path, _on_opened)

    def _frame(self, prim_path: str) -> None:
        try:
            from omni.kit.viewport.utility import frame_viewport_prims
            viewport_api = self._viewport_window.viewport_api
            frame_viewport_prims(viewport_api, prims=[prim_path])
        except Exception as exc:
            carb.log_warn(f"[PrimPreviewWidget] frame failed: {exc}")
