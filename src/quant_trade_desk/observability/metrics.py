"""Small Prometheus-compatible metric registry."""

from __future__ import annotations

from collections import defaultdict
from threading import RLock


class MetricsRegistry:
    def __init__(self) -> None:
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._types: dict[str, str] = {}
        self._lock = RLock()

    @staticmethod
    def _key(name: str, labels: dict[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
        return name, tuple(sorted(labels.items()))

    def increment(self, name: str, value: float = 1, **labels: str) -> None:
        with self._lock:
            self._types[name] = "counter"
            self._values[self._key(name, labels)] += value

    def gauge(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._types[name] = "gauge"
            self._values[self._key(name, labels)] = value

    def render(self) -> str:
        with self._lock:
            lines: list[str] = []
            emitted: set[str] = set()
            for (name, label_items), value in sorted(self._values.items()):
                if name not in emitted:
                    lines.append(f"# TYPE {name} {self._types[name]}")
                    emitted.add(name)
                label_text = ""
                if label_items:
                    encoded = ",".join(
                        f'{key}="{val.replace(chr(34), chr(92) + chr(34))}"'
                        for key, val in label_items
                    )
                    label_text = f"{{{encoded}}}"
                lines.append(f"{name}{label_text} {value}")
            return "\n".join(lines) + ("\n" if lines else "")
