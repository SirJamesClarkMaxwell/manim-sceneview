"""Silnik sceny (Manim CE albo manimgl) z MRO jej klasy — bez importu żadnego silnika.

Porównanie z klasą `Scene` modułu już załadowanego w `sys.modules`: scena gospodarza istnieje,
więc jej silnik jest zaimportowany; drugi silnik nie jest ładowany, także gdy jest zainstalowany.
"""

import importlib.util
import sys

SCENE_MODULES = {"ce": "manim.scene.scene", "gl": "manimlib.scene.scene"}


def engine_of(scene) -> str:
    """``"ce"`` albo ``"gl"`` dla instancji lub klasy sceny."""
    cls = scene if isinstance(scene, type) else type(scene)
    for engine, module in SCENE_MODULES.items():
        base = getattr(sys.modules.get(module), "Scene", None)
        if base is not None and issubclass(cls, base):
            return engine
    if not any(importlib.util.find_spec(name.split(".")[0]) for name in SCENE_MODULES.values()):
        raise ImportError(
            "No Manim engine installed: pip install 'manim-sceneview[ce]' for Manim Community "
            "or 'manim-sceneview[gl]' for manimgl"
        )
    raise TypeError(f"{cls.__qualname__} is not a Manim Community or manimgl Scene")
