from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHANNELS, DEFAULT_BANDS, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device = data["device"]
    coordinator = data["coordinator"]

    entities = [AFSSwitch(coordinator, device, entry)]

    for band in DEFAULT_BANDS:
        for channel in CHANNELS:
            entities.append(BandMuteSwitch(coordinator, device, entry, band, channel))

    async_add_entities(entities)


class AFSSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of the AFS Status switch."""

    def __init__(self, coordinator, device, entry):
        super().__init__(coordinator)
        self._device = device
        self._attr_name = "AFS Status"
        self._attr_unique_id = f"{entry.entry_id}_afs_status"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("afs", {}).get("enabled", False)

    async def async_turn_on(self, **kwargs) -> None:
        try:
            await self._device.async_set_afs_enabled(True)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to communicate with DriveRack PA2: {err}"
            ) from err

    async def async_turn_off(self, **kwargs) -> None:
        try:
            await self._device.async_set_afs_enabled(False)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to communicate with DriveRack PA2: {err}"
            ) from err


class BandMuteSwitch(CoordinatorEntity, SwitchEntity):
    """Mute switch entity per band and channel."""

    def __init__(self, coordinator, device, entry, band: str, channel: str):
        super().__init__(coordinator)
        self._device = device
        self._band = band
        self._channel = channel
        self._attr_name = f"Band {band} {channel} Mute"
        self._attr_unique_id = f"{entry.entry_id}_mute_{band}_{channel}"

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        active_bands = self.coordinator.data.get("meters", {}).get("limiter", {}).keys()
        return self._band in active_bands

    @property
    def is_on(self) -> bool:
        return (
            self.coordinator.data.get("mutes", {})
            .get(self._band, {})
            .get(self._channel, False)
        )

    async def async_turn_on(self, **kwargs) -> None:
        try:
            await self._device.async_set_mute(self._band, self._channel, True)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            raise HomeAssistantError(f"Failed to execute mute command: {err}") from err

    async def async_turn_off(self, **kwargs) -> None:
        try:
            await self._device.async_set_mute(self._band, self._channel, False)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to execute unmute command: {err}"
            ) from err
