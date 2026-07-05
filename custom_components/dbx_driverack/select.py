from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DriveRackPresetSelect(
                data["coordinator"], data["device"], entry, data["presets"]
            )
        ]
    )


class DriveRackPresetSelect(CoordinatorEntity, SelectEntity):
    """Dropdown component for changing active preset indices."""

    def __init__(self, coordinator, device, entry, presets: dict):
        super().__init__(coordinator)
        self._device = device
        self._presets = presets
        self._attr_name = "Preset"
        self._attr_unique_id = f"{entry.entry_id}_preset_select"
        self._attr_options = list(self._presets.values())

    @property
    def current_option(self) -> str | None:
        info_data = self.coordinator.data.get("info") or {}
        current_id = info_data.get("current_preset")
        if current_id is None:
            return None
        return self._presets.get(int(current_id))

    async def async_select_option(self, option: str) -> None:
        preset_id = next((k for k, v in self._presets.items() if v == option), None)
        if preset_id is not None:
            try:
                await self._device.async_recall_preset(preset_id)
                await self.coordinator.async_request_refresh()
            except Exception as err:
                raise HomeAssistantError(
                    f"Failed to recall preset target: {err}"
                ) from err
