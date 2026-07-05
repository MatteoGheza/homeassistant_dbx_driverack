import logging

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    event_entity = DriveRackLarsenEvent(entry)

    # Register the receiver inside our global list defined in __init__.py
    data["larsen_callbacks"].append(event_entity.handle_larsen_event)
    async_add_entities([event_entity])


class DriveRackLarsenEvent(EventEntity):
    """Event entity capturing active Larsen/Feedback filtering data updates."""

    def __init__(self, entry):
        self._attr_name = "Larsen Feedback Event"
        self._attr_unique_id = f"{entry.entry_id}_larsen_event"
        # Match types from on_larsen_detected signature
        self._attr_event_types = ["larsen_detected", "larsen_cleared"]

    @callback
    def handle_larsen_event(self, band: int, freq: str, active: bool) -> None:
        """Trigger native HA platform state events with metadata injection."""
        event_type = "larsen_detected" if active else "larsen_cleared"
        _LOGGER.debug(
            "Larsen Event Triggered: %s, Band: %s, Frequency: %s",
            event_type,
            band,
            freq,
        )
        self._trigger_event(
            event_type, {"band": band, "frequency": freq, "active": active}
        )
        self.async_write_ha_state()
