"""Support for Xinao Energy Analysis sensors."""
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
from .const import DOMAIN, SENSOR_TYPES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xinao Energy sensors from a config entry."""
    coordinator: XinaoEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Add main sensors
    for sensor_type, sensor_info in SENSOR_TYPES.items():
        entities.append(
            XinaoEnergySensor(
                coordinator=coordinator,
                entry=entry,
                sensor_type=sensor_type,
                sensor_info=sensor_info,
            )
        )

    # Add daily usage sensor
    entities.append(
        XinaoEnergyDailyUsageSensor(
            coordinator=coordinator,
            entry=entry,
        )
    )

    # Add ladder price sensor
    entities.append(
        XinaoEnergyLadderPriceSensor(
            coordinator=coordinator,
            entry=entry,
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
        if sensor_info.get("device_class"):
            self._attr_device_class = sensor_info["device_class"]

        # Set state class if available
        if sensor_info.get("state_class"):
            self._attr_state_class = sensor_info["state_class"]

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Xinao Energy ({entry.data['payment_no']})",
            "manufacturer": "Xinao Energy",
            "model": "Energy Analysis",
        }

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        # Map sensor type to data key
        key_map = {
            "balance": "balance",
            "arrears_amount": "arrearsAmount",
            "current_month_usage": "currentMonthUsage",
            "current_month_cost": "currentMonthCost",
            "total_gas_count": "totalGasCount",
            "available_days": "availableDays",
        }

        key = key_map.get(self._sensor_type)
        if key:
            value = self.coordinator.data.get(key)
            if value is not None:
                # Convert string numbers to float
                if isinstance(value, str):
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

        # Add ladder cycle description for cost/usage sensors
        if self._sensor_type in ["current_month_usage", "current_month_cost"]:
            ladder_cycle = self.coordinator.data.get("ladderCycleDesc")
            if ladder_cycle:
                attrs["ladder_cycle"] = ladder_cycle

        # Add last month balance if available
        if self._sensor_type == "balance":
            last_month_balance = self.coordinator.data.get("lastMonthBalance")
            if last_month_balance is not None:
                attrs["last_month_balance"] = last_month_balance

        # Add current month estimate cost if available
        if self._sensor_type == "current_month_cost":
            estimate = self.coordinator.data.get("currentMonthEstimateCost")
            if estimate is not None:
                attrs["estimated_cost"] = estimate

        return attrs


class XinaoEnergyDailyUsageSensor(CoordinatorEntity, SensorEntity):
    """Representation of daily usage sensor with history."""

    def __init__(
        self,
        coordinator: XinaoEnergyCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_daily_usage"
        self._attr_translation_key = "daily_usage"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:calendar-today"
        self._attr_native_unit_of_measurement = "m³"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Xinao Energy ({entry.data['payment_no']})",
            "manufacturer": "Xinao Energy",
            "model": "Energy Analysis",
        }

    @property
    def native_value(self) -> float | None:
        """Return today's usage."""
        if self.coordinator.data is None:
            return None

        daily_list = self.coordinator.data.get("dailyUsageList", [])
        if daily_list and len(daily_list) > 0:
            # Get the latest entry (today)
            latest = daily_list[-1]
            usage = latest.get("usage")
            if usage:
                try:
                    return float(usage)
                except ValueError:
                    return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return daily usage history."""
        if self.coordinator.data is None:
            return {}

        daily_list = self.coordinator.data.get("dailyUsageList", [])

        attrs = {}
        if daily_list:
            attrs["history"] = daily_list
            attrs["total_days"] = len(daily_list)

            # Calculate statistics
            usages = []
            for item in daily_list:
                try:
                    usages.append(float(item.get("usage", 0)))
                except ValueError:
                    continue

            if usages:
                attrs["average_usage"] = round(sum(usages) / len(usages), 2)
                attrs["max_usage"] = max(usages)
                attrs["min_usage"] = min(usages)
                attrs["total_usage"] = round(sum(usages), 2)

        return attrs


class XinaoEnergyLadderPriceSensor(CoordinatorEntity, SensorEntity):
    """Representation of ladder price sensor."""

    def __init__(
        self,
        coordinator: XinaoEnergyCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ladder_price"
        self._attr_translation_key = "ladder_price"
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:stairs"
        self._attr_native_unit_of_measurement = "CNY/m³"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Xinao Energy ({entry.data['payment_no']})",
            "manufacturer": "Xinao Energy",
            "model": "Energy Analysis",
        }

    @property
    def native_value(self) -> float | None:
        """Return current applicable ladder price."""
        if self.coordinator.data is None:
            return None

        ladder_list = self.coordinator.data.get("ladderDtoList", [])
        current_usage = self.coordinator.data.get("currentMonthUsage")

        if ladder_list and current_usage:
            try:
                usage_value = float(current_usage)
                # Find applicable ladder tier
                for ladder in ladder_list:
                    start = ladder.get("ladderStartValue", 0)
                    end = ladder.get("ladderEndValue", 999999999)
                    if start <= usage_value < end:
                        return ladder.get("gasPrice")
            except (ValueError, TypeError):
                pass

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return ladder price tiers."""
        if self.coordinator.data is None:
            return {}

        attrs = {}

        ladder_list = self.coordinator.data.get("ladderDtoList", [])
        if ladder_list:
            attrs["ladder_tiers"] = ladder_list
            attrs["total_tiers"] = len(ladder_list)

        ladder_cycle = self.coordinator.data.get("ladderCycleDesc")
        if ladder_cycle:
            attrs["cycle_description"] = ladder_cycle

        return attrs
