from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHANNELS, DEFAULT_BANDS, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = []

    # Input clipping binary sensors are always available
    for ch in CHANNELS:
        entities.append(InputClippingSensor(coordinator, entry, ch))

    # Always generate entities for all 3 standard band limiters at startup
    for band in DEFAULT_BANDS:
        entities.append(LimiterTriggeredSensor(coordinator, entry, band))

    async_add_entities(entities)


class InputClippingSensor(CoordinatorEntity, BinarySensorEntity):
    """Detects signal input clipping alerts."""

    def __init__(self, coordinator, entry, channel: str):
        super().__init__(coordinator)
        self._channel = channel
        self._attr_name = f"Input {channel} Clipping"
        self._attr_unique_id = f"{entry.entry_id}_clipping_{channel}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return (
            self.coordinator.data.get("meters", {})
            .get("input", {})
            .get(self._channel, {})
            .get("clip", False)
        )


class LimiterTriggeredSensor(CoordinatorEntity, BinarySensorEntity):
    """Monitors if processing loop limiters have been tripped."""

    def __init__(self, coordinator, entry, band: str):
        super().__init__(coordinator)
        self._band = band
        self._attr_name = f"{band} Band Limiter Triggered"
        self._attr_unique_id = f"{entry.entry_id}_limiter_{band}"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def available(self) -> bool:
        """Return True if this band is actively used in the current preset setup."""
        if not self.coordinator.last_update_success:
            return False

        active_bands = self.coordinator.data.get("meters", {}).get("limiter", {}).keys()
        return self._band in active_bands

    @property
    def is_on(self) -> bool:
        return (
            self.coordinator.data.get("meters", {})
            .get("limiter", {})
            .get(self._band, {})
            .get("triggered", False)
        )
