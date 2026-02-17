"""Watch shim used by the UI and lightweight scripts.

Behavior:
- Try to integrate with native watcher/CLI if available (best-effort).
- Fallback to an in-process registry returning a WatchProxy.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict
import uuid
import threading

from .errors import GlueError


class WatcherRegistry:
    """Simple in-process registry for WatchProxy objects."""

    def __init__(self):
        self._lock = threading.RLock()
        self._data: Dict[str, WatchProxy] = {}

    def register(self, proxy: "WatchProxy") -> str:
        with self._lock:
            self._data[proxy.id] = proxy
            return proxy.id

    def get(self, id: str):
        with self._lock:
            return self._data.get(id)


_REGISTRY = WatcherRegistry()


@dataclass
class WatchProxy:
    """Lightweight wrapper returned by `watch()`.

    The object holds the original value for convenience and serializable metadata.
    """

    value: Any
    name: str | None = None
    scope: str | None = None
    file_path: str | None = None
    id: str | None = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def get(self):
        return self.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "scope": self.scope,
            "file_path": self.file_path,
            "value_repr": repr(self.value),
        }


def _try_native_register(proxy: WatchProxy) -> bool:
    """Best-effort attempt to register the proxy with native watcher/CLI.

    We don't require this to succeed; it's a convenience for environments
    where the watcher core is installed. We opt for a safe, import-based
    approach so this never crashes the caller.
    """
    try:
        # Try to import watcher integration points; if present, call a
        # registration function if available.
        import watcher.core.event_bridge as event_bridge  # type: ignore

        if hasattr(event_bridge, "register_watch_proxy"):
            try:
                event_bridge.register_watch_proxy(proxy.to_dict())
                return True
            except Exception:
                return False
    except Exception:
        return False

    return False


def watch(value: Any, name: str | None = None, scope: str | None = None, file_path: str | None = None) -> WatchProxy:
    """Create and register a `WatchProxy` for `value`.

    This function is intentionally lightweight and safe to call from UI
    code or end-user scripts. It will attempt to register with any native
    watcher if available, and otherwise stay in-process.
    """
    proxy = WatchProxy(value=value, name=name, scope=scope, file_path=file_path)

    # Try native registration; ignore failures.
    try:
        _try_native_register(proxy)
    except Exception as e:  # pragma: no cover - extremely defensive
        raise GlueError("watch integration failed: %s" % (e,))

    _REGISTRY.register(proxy)
    return proxy
