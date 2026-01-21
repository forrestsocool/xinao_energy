"""Support for Xinao Energy sensors."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import XinaoEnergyCoordinator
from .const import DOMAIN, SENSOR_TYPES, CONF_DEVICE_ID


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xinao Energy sensors from a config entry."""
    coordinator: XinaoEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for sensor_type, sensor_info in SENSOR_TYPES.items():
        entities.append(
            XinaoEnergySensor(
                coordinator=coordinator,
                entry=entry,
                sensor_type=sensor_type,
                sensor_info=sensor_info,
            )
        )

    async_add_entities(entities)


class XinaoEnergySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Xinao Energy sensor."""

    def __init__(
        self,
        coordinator: XinaoEnergyCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        sensor_info: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_translation_key = sensor_type
        self._attr_has_entity_name = True
        self._attr_native_unit_of_measurement = sensor_info.get("unit")
        self._attr_icon = sensor_info.get("icon")
        self._sensor_type = sensor_type

        # Set device class if available
        device_class = sensor_info.get("device_class")
        if device_class:
            if device_class == "monetary":
                self._attr_device_class = SensorDeviceClass.MONETARY
            elif device_class == "gas":
                self._attr_device_class = SensorDeviceClass.GAS
            elif device_class == "timestamp":
                self._attr_device_class = SensorDeviceClass.TIMESTAMP

        # Set state class if available
        state_class = sensor_info.get("state_class")
        if state_class:
            if state_class == "total":
                self._attr_state_class = SensorStateClass.TOTAL
            elif state_class == "total_increasing":
                self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            elif state_class == "measurement":
                self._attr_state_class = SensorStateClass.MEASUREMENT

        device_id = entry.data.get(CONF_DEVICE_ID, "unknown")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Xinao Gas ({device_id})",
            "manufacturer": "Xinao Energy",
            "model": "Gas Meter",
        }

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        value = self.coordinator.data.get(self._sensor_type)
        
        if value is not None:
            # Convert string numbers to float if needed
            if isinstance(value, str) and self._sensor_type != "last_recharge_time":
                try:
                    return float(value)
                except ValueError:
                    return value
            return value
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if self.coordinator.data is None:
            return {}

        attrs = {}

        # Add gas price to usage sensors for reference
        if self._sensor_type in ["today_usage", "monthly_usage"]:
            gas_price = self.coordinator.data.get("gas_price")
            if gas_price is not None:
                attrs["gas_price"] = gas_price

        # Add balance to cost sensors for reference
        if self._sensor_type in ["today_cost", "monthly_cost"]:
            balance = self.coordinator.data.get("balance")
            if balance is not None:
                attrs["current_balance"] = balance

        return attrs
