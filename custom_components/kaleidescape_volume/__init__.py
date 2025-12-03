import logging
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT
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

    # 🔴 Adjust this to match your event dict shape
    def _handle_event(evt: dict) -> None:
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

            # Enable the volume events
            if hasattr(client, "enable_volume_events"):
                try:
                    await client.enable_volume_events()
                    _LOGGER.info("Requested Kaleidescape volume events")
                except Exception:
                    _LOGGER.exception("Failed to enable volume events")

            # Replace this with whatever your client uses to keep reading
            if hasattr(client, "run_forever"):
                await client.run_forever()
            else:
                # Fallback: keep the connection alive yourself if needed
                while True:
                    await client.poll()  # or similar
        except Exception:
            _LOGGER.exception("Kaleidescape volume bridge crashed")

    hass.loop.create_task(_runner())
    return True
