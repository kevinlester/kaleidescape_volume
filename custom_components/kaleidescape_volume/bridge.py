"""Connection and dispatcher helpers for the Kaleidescape volume bridge."""

import logging
from typing import Any, Callable, Optional

_LOGGER = logging.getLogger(__name__)


async def connect_device(device: Any, host: str, port: int) -> bool:
    """Connect to the Kaleidescape device; return True on success."""
    try:
        await device.connect()
        _LOGGER.info("Connected to Kaleidescape at %s:%s", host, port)
        return True
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to connect to Kaleidescape device")
        return False


def connect_dispatcher(device: Any, callback: Callable[[Any], None]) -> Optional[Any]:
    """Register a dispatcher listener and return the connection handle."""
    dispatcher = getattr(device, "dispatcher", None)
    if dispatcher is None or not hasattr(dispatcher, "connect"):
        _LOGGER.warning(
            "Kaleidescape device has no 'dispatcher'; "
            "volume button events will not be received."
        )
        return None

    try:
        connection = dispatcher.connect(callback)
        _LOGGER.debug("Connected Kaleidescape dispatcher listener")
        return connection
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to connect Kaleidescape dispatcher")
        return None


def disconnect_dispatcher(connection: Optional[Any]) -> None:
    """Unsubscribe the dispatcher listener if a connection exists."""
    if connection is None:
        return

    try:
        disconnect = getattr(connection, "disconnect", None)
        if callable(disconnect):
            disconnect()
            _LOGGER.debug("Disconnected Kaleidescape dispatcher listener")
    except Exception:  # noqa: BLE001
        _LOGGER.exception(
            "Error while disconnecting Kaleidescape dispatcher listener"
        )


async def disconnect_device(device: Any) -> None:
    """Close the device connection if supported."""
    try:
        if hasattr(device, "disconnect"):
            await device.disconnect()
        elif hasattr(device, "close"):
            await device.close()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Error while closing Kaleidescape device")
