"""Repeat HA events while a button is held."""

import asyncio
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class VolumeRepeatManager:
    """Manage repeated HA bus events while a button is held."""

    def __init__(
        self,
        hass: Any,
        interval: float,
        event_type: str = "kaleidescape_volume_button",
    ) -> None:
        self._hass = hass
        self._interval = interval
        self._event_type = event_type
        self._tasks: dict[str, asyncio.Task] = {}

    async def _repeat(self, event_name: str) -> None:
        """Internal loop: fire events until cancelled."""
        try:
            # 🔹 Wait one interval before the *first* repeat
            await asyncio.sleep(self._interval)
            
            while True:
                _LOGGER.debug("Kaleidescape volume event: %s", event_name)
                self._hass.bus.async_fire(self._event_type, {"event": event_name})
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            _LOGGER.debug("Volume repeat task cancelled for %s", event_name)

    def start(self, event_name: str) -> None:
        """Start repeating the given event name."""
        task = self._tasks.get(event_name)
        if task is not None and not task.done():
            return

        _LOGGER.debug("Starting repeat task for %s", event_name)
        self._tasks[event_name] = self._hass.async_create_task(
            self._repeat(event_name)
        )

    def stop(self, event_name: str) -> None:
        """Stop repeating the given event name, if running."""
        task = self._tasks.pop(event_name, None)
        if task is None:
            return

        if not task.done():
            _LOGGER.debug("Stopping repeat task for %s", event_name)
            task.cancel()

    def stop_all(self) -> None:
        """Stop all active repeat tasks."""
        for name in list(self._tasks.keys()):
            self.stop(name)
