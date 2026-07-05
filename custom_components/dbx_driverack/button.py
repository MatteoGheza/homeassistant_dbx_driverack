import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHANNELS, DEFAULT_BANDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    device = data["device"]
    coordinator = data["coordinator"]

    async_add_entities(
        [
            DriveRackMuteAllButton(coordinator, device, entry),
            DriveRackUnmuteAllButton(coordinator, device, entry),
        ]
    )


class DriveRackMuteAllButton(CoordinatorEntity, ButtonEntity):
    """Button to mute all audio output paths simultaneously."""

    def __init__(self, coordinator, device, entry):
        super().__init__(coordinator)
        self._device = device
        self._attr_name = "Mute All"
        self._attr_unique_id = f"{entry.entry_id}_mute_all"
        self._attr_icon = "mdi:volume-mute"

    async def async_press(self) -> None:
        try:
            if hasattr(self._device, "async_mute_all"):
                await self._device.async_mute_all()
            else:
                for band in DEFAULT_BANDS:
                    for channel in CHANNELS:
                        await self._device.async_set_mute(band, channel, True)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to execute master mute action: {err}"
            ) from err


class DriveRackUnmuteAllButton(CoordinatorEntity, ButtonEntity):
    """Button to restore all audio output pathways simultaneously."""

    def __init__(self, coordinator, device, entry):
        super().__init__(coordinator)
        self._device = device
        self._attr_name = "Unmute All"
        self._attr_unique_id = f"{entry.entry_id}_unmute_all"
        self._attr_icon = "mdi:volume-high"

    async def async_press(self) -> None:
        try:
            await self._device.async_unmute_all()
            await self.coordinator.async_request_refresh()
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to execute master unmute action: {err}"
            ) from err
