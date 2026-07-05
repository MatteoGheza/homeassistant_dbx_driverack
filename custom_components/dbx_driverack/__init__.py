import asyncio
import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydbxdriverack.connection import PA2Connection
from pydbxdriverack.device import PA2Device

from .const import CHANNELS, CONF_HOST, CONF_PASSWORD, DEFAULT_BANDS, DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["switch", "binary_sensor", "sensor", "select", "event", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up dbx DriveRack PA2 from a config entry."""
    host = entry.data[CONF_HOST]
    password = entry.data[CONF_PASSWORD]

    conn = PA2Connection(host, password=password)
    try:
        await conn.connect()
    except Exception as err:
        _LOGGER.error("Failed to connect to DriveRack PA2 at %s: %s", host, err)
        return False

    device = PA2Device(conn)
    await device.async_update_info()
    presets = await device.async_get_preset_names()

    # Initialize entry context dictionary data mapping variables
    hass.data.setdefault(DOMAIN, {})
    entry_data = {
        "device": device,
        "conn": conn,
        "coordinator": None,
        "larsen_callbacks": [],
        "presets": presets,
        "is_online": True,
        "last_reconnect_attempt": 0,
        "monitor_task": None,
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data

    def on_larsen_detected(band: int, freq: str, active: bool):
        for callback_func in entry_data["larsen_callbacks"]:
            callback_func(band, freq, active)

    # Helper function to safely spawn the background Larsen pushing listener task
    def start_larsen_monitor():
        if entry_data["monitor_task"]:
            entry_data["monitor_task"].cancel()
        entry_data["monitor_task"] = hass.async_create_background_task(
            device.async_monitor_afs_filters(on_larsen_detected),
            name=f"dbx_driverack_larsen_monitor_{entry.entry_id}",
        )

    start_larsen_monitor()

    async def async_update_data():
        now = time.time()

        # Connection recovery logic
        if not entry_data["is_online"]:
            # Enforce 30-second retry intervals
            if now - entry_data["last_reconnect_attempt"] < 30:
                raise UpdateFailed(
                    "DriveRack PA2 is offline. Waiting for next 30s reconnect window."
                )

            _LOGGER.info("Attempting to reconnect to DriveRack PA2 at %s...", host)
            entry_data["last_reconnect_attempt"] = now
            try:
                await conn.connect()
                await device.async_update_info()
                entry_data["is_online"] = True
                start_larsen_monitor()
                _LOGGER.info("Successfully reconnected to DriveRack PA2 at %s!", host)
            except Exception as err:
                raise UpdateFailed(f"Reconnection attempt failed: {err}")

        try:
            # Main polling execution pass
            meters = await device.async_poll_meters()
            afs_status = await device.async_get_afs_status()
            info_payload = await device.async_update_info()

            bands = list(meters.get("limiter", {}).keys()) or DEFAULT_BANDS

            mute_tasks = []
            mute_keys = []
            for band in bands:
                for channel in CHANNELS:
                    mute_tasks.append(device.async_get_mute_state(band, channel))
                    mute_keys.append((band, channel))

            mute_results = await asyncio.gather(*mute_tasks, return_exceptions=True)

            mutes_dict = {}
            for (band, channel), result in zip(mute_keys, mute_results):
                if isinstance(result, Exception):
                    mutes_dict.setdefault(band, {})[channel] = False
                else:
                    mutes_dict.setdefault(band, {})[channel] = bool(result)

            return {
                "meters": meters,
                "afs": afs_status,
                "info": info_payload,
                "mutes": mutes_dict,
                "device_object": device,
            }
        except Exception as err:
            if entry_data["is_online"]:
                _LOGGER.warning("Lost connection to DriveRack PA2 at %s: %s", host, err)
                entry_data["is_online"] = False
                entry_data["last_reconnect_attempt"] = now
                if entry_data["monitor_task"]:
                    entry_data["monitor_task"].cancel()
            raise UpdateFailed(f"Communication fault: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"dbx_driverack_{host}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=1),
    )
    await coordinator.async_config_entry_first_refresh()
    entry_data["coordinator"] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        if data["monitor_task"]:
            data["monitor_task"].cancel()
        await data["conn"].disconnect()
    return unload_ok
