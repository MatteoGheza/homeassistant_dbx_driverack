from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHANNELS, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([InputLevelSensor(data["coordinator"], entry, ch) for ch in CHANNELS])

class InputLevelSensor(CoordinatorEntity, SensorEntity):
    """Reads input channel sound amplitude level meters."""

    def __init__(self, coordinator, entry, channel: str):
        super().__init__(coordinator)
        self._channel = channel
        self._attr_name = f"Input {channel} Level"
        self._attr_unique_id = f"{entry.entry_id}_level_{channel}"
        self._attr_native_unit_of_measurement = "dB"
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        raw_value = self.coordinator.data.get("meters", {}).get("input", {}).get(self._channel, {}).get("level")

        if raw_value is None:
            return None

        if isinstance(raw_value, str):
            try:
                return float(raw_value.replace("dB", "").replace(" ", ""))
            except ValueError:
                return None

        try:
            return float(raw_value)
        except (ValueError, TypeError):
            return None
