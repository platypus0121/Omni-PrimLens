# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb
import omni.ext
import omni.usd

from .preview_widget import PrimPreviewWidget


def some_public_function(x: int):
    """This is a public function that can be called from other extensions."""
    print(f"[omni.prim.primlens] some_public_function was called with {x}")
    return x ** x


class MyExtension(omni.ext.IExt):
    """PrimLens – isolated 3D Prim Preview viewport."""

    def on_startup(self, _ext_id):
        print("[omni.prim.primlens] Extension startup")
        self._preview_widget = PrimPreviewWidget()
        self._stage_event_sub = (
            omni.usd.get_context()
            .get_stage_event_stream()
            .create_subscription_to_pop(self._on_stage_event, name="primlens_selection")
        )

    def on_shutdown(self):
        print("[omni.prim.primlens] Extension shutdown")
        self._stage_event_sub = None
        if self._preview_widget is not None:
            self._preview_widget.destroy()
            self._preview_widget = None

    def _on_stage_event(self, event) -> None:
        if event.type != int(omni.usd.StageEventType.SELECTION_CHANGED):
            return
        try:
            selected = omni.usd.get_context().get_selection().get_selected_prim_paths()
            if selected and self._preview_widget is not None:
                self._preview_widget.focus_on_prim(selected[0])
        except Exception as exc:
            carb.log_warn(f"[omni.prim.primlens] selection handler error: {exc}")
