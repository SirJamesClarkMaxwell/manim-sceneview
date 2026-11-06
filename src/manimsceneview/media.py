"""Metadane pliku wideo bez dekodowania całości (przeniesione z `manimcue.media`)."""

from functools import cache
from pathlib import Path

import av


def video_info(file: Path | str) -> tuple[float, float]:
    """(długość w s, fps) pierwszego strumienia wideo, z metadanych — bez dekodowania całości.

    Pamięć podręczna po ścieżce, rozmiarze i mtime: jeden render bywa źródłem wielu widoków.
    """
    path = Path(file).resolve()
    stat = path.stat()
    return _video_info(path, stat.st_size, stat.st_mtime_ns)


@cache
def _video_info(file: Path, size: int, mtime_ns: int) -> tuple[float, float]:
    with av.open(str(file)) as container:
        stream = container.streams.video[0]
        rate = stream.average_rate
        if stream.duration is None or stream.time_base is None or not rate:
            raise ValueError(f"Unknown duration or frame rate of video {file}")
        return float(stream.duration * stream.time_base), float(rate)
