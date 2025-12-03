import asyncio
import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

# ⬇️ Adjust this import to match your fork
# e.g. from pykaleidescape import KaleidescapeClient
from pykaleidescape import KaleidescapeClient

_LOGGER = logging.getLogger(__name__)

DOMAIN = "kaleidescape_volume"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=10000): cv.port,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Kaleidescape volume sidecar."""
    conf = config.get(DOMAIN)
    if conf is None:
        _LOGGER.debug("No %s config found; not starting", DOMAIN)
        return True

    host = conf[CONF_HOST]
    port = conf[CONF_PORT]

    _LOGGER.info("Starting Kaleidescape volume bridge for %s:%s", host, port)

    client = KaleidescapeClient(host, port=port)

    # Event used to keep the runner alive until HA is stopping
    stop_event: asyncio.Event = asyncio.Event()

    async def _async_stop(event: Any) -> None:
        """Handle Home Assistant stop to shut down the client cleanly."""
        _LOGGER.info("Stopping Kaleidescape volume bridge for %s:%s", host, port)
        stop_event.set()

    # When Home Assistant is shutting down, notify our runner
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop)

    def _handle_event(evt: Dict[str, Any]) -> None:
        """
        Expected example evt from your fork:

            {
              "type": "USER_DEFINED_EVENT",
              "name": "VOLUME_UP_PRESS",
              "raw": "USER_DEFINED_EVENT:VOLUME_UP_PRESS"
            }

        We filter for PRESS events only.
        """
        evt_type = evt.get("type")
        name = (evt.get("name") or "").upper()

        if evt_type != "USER_DEFINED_EVENT":
            return

        if not (name.startswith("VOLUME_") and name.endswith("_PRESS")):
            return

        _LOGGER.debug("Kaleidescape volume event: %s", name)

        hass.bus.fire(
            "kaleidescape_volume_button",
            {"event": name},
        )

    client.add_event_listener(_handle_event)

    async def _runner() -> None:
        try:
            await client.connect()

            # Enable the volume events if available on your fork
            if hasattr(client, "enable_volume_events"):
                try:
                    await client.enable_volume_events()
                    _LOGGER.info("Requested Kaleidescape volume events")
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Failed to enable volume events")

            # Keep the connection open until Home Assistant is stopping.
            await stop_event.wait()

        except Exception:  # noqa: BLE001
            _LOGGER.exception("Kaleidescape volume bridge crashed")
        finally:
            # Try to disconnect/close cleanly on shutdown.
            try:
                if hasattr(client, "disconnect"):
                    await client.disconnect()
                elif hasattr(client, "close"):
                    await client.close()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Error while closing Kaleidescape client")

    hass.async_create_task(_runner())
    return True
