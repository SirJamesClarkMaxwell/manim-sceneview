"""Gotowe sceny Manima jako mobjecty w innej scenie — Manim Community i manimgl.

Import pakietu nie ładuje żadnego silnika; `SceneView` wybiera go z klasy sceny gospodarza.
"""

from manimsceneview.child_view import ChildView
from manimsceneview.frame_source import FrameSource
from manimsceneview.scene_view import SceneView

__all__ = ["ChildView", "FrameSource", "SceneView"]
