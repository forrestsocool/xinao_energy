"""The Xinao Energy Analysis integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import XinaoEnergyAPI
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Xinao Energy Analysis from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get configuration
    token = entry.data["token"]
    payment_no = entry.data["payment_no"]
    company_code = entry.data["company_code"]

    # Get update interval from options or data
    update_interval = entry.options.get(
        "update_interval",
        entry.data.get("update_interval", DEFAULT_UPDATE_INTERVAL)
    )

    # Create API client
    api = XinaoEnergyAPI(
        token=token,
        payment_no=payment_no,
        company_code=company_code,
    )

    # Create coordinator
    coordinator = XinaoEnergyCoordinator(
        hass,
        api=api,
        update_interval=timedelta(minutes=update_interval),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Setup options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class XinaoEnergyCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Xinao Energy data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: XinaoEnergyAPI,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.api = api

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            data = await self.hass.async_add_executor_job(
                self.api.get_energy_analysis
            )

            if data is None or data.get("resultCode") != 200:
                raise UpdateFailed("Failed to fetch energy data")

            return data.get("data", {})

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
