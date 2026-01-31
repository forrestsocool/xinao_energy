"""The Xinao Energy integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import XinaoEnergyAPI
from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_CITY_ID,
    CONF_TOKEN,
    CONF_DEVICE_ID,
    CONF_CITY_ID,
    CONF_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

STORAGE_VERSION = 3  # Keep at 3 for Store compatibility
STORAGE_MINOR_VERSION = 4  # v4: Fix UTC timezone issue in order time comparison
STORAGE_KEY = f"{DOMAIN}_data"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Xinao Energy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get configuration
    token = entry.data[CONF_TOKEN]
    device_id = entry.data[CONF_DEVICE_ID]
    city_id = entry.data.get(CONF_CITY_ID, DEFAULT_CITY_ID)

    # Get update interval from options or data
    update_interval = entry.options.get(
        CONF_UPDATE_INTERVAL,
        entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
    )

    # Create API client
    api = XinaoEnergyAPI(
        token=token,
        device_id=device_id,
        city_id=city_id,
    )

    # Set up token refresh callback
    async def async_update_token(new_token: str) -> None:
        """Update token in config entry when refreshed."""
        new_data = {**entry.data, CONF_TOKEN: new_token}
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.info("Token updated in config entry")

    def update_token_sync(new_token: str) -> None:
        """Sync wrapper for token update."""
        hass.loop.call_soon_threadsafe(
            lambda: hass.async_create_task(async_update_token(new_token))
        )

    api.set_token_refresh_callback(update_token_sync)

    # Create storage for persistent data
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")

    # Create coordinator
    coordinator = XinaoEnergyCoordinator(
        hass,
        api=api,
        store=store,
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
        store: Store,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.api = api
        self.store = store
        self._stored_data: dict[str, Any] | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_load_stored_data(self) -> dict[str, Any]:
        """Load stored data from disk.
        
        If upgrading from v3, migrate data by clearing processed_order_ids
        to re-process orders with fixed UTC timezone handling.
        """
        if self._stored_data is None:
            loaded_data = await self.store.async_load()
            
            if loaded_data is None:
                # No existing data
                self._stored_data = {}
            elif loaded_data.get("_minor_version", 3) < STORAGE_MINOR_VERSION:
                # Migration from older version: keep start_balance, clear order IDs
                _LOGGER.info(
                    "Migrating storage data from minor v%s to v%s (fixing UTC timezone issue)",
                    loaded_data.get("_minor_version", "unknown"),
                    STORAGE_MINOR_VERSION,
                )
                
                daily_data = loaded_data.get("daily", {})
                monthly_data = loaded_data.get("monthly", {})
                
                # Keep start_balance and start_time, but clear processed orders
                # This allows re-processing with fixed timezone handling
                if daily_data:
                    daily_data["processed_order_ids"] = []
                    daily_data["recharge_total"] = 0.0
                    _LOGGER.info(
                        "Daily data migrated: keeping start_balance=%.2f, start_time=%s",
                        daily_data.get("start_balance", 0),
                        daily_data.get("start_time", "unknown"),
                    )
                
                if monthly_data:
                    monthly_data["processed_order_ids"] = []
                    monthly_data["recharge_total"] = 0.0
                    _LOGGER.info(
                        "Monthly data migrated: keeping start_balance=%.2f, start_time=%s",
                        monthly_data.get("start_balance", 0),
                        monthly_data.get("start_time", "unknown"),
                    )
                
                self._stored_data = {
                    "daily": daily_data,
                    "monthly": monthly_data,
                    "last_balance": loaded_data.get("last_balance"),
                    "last_update": loaded_data.get("last_update"),
                    "_minor_version": STORAGE_MINOR_VERSION,
                }
                
                # Save migrated data
                await self._async_save_stored_data()
            else:
                self._stored_data = loaded_data
                
        return self._stored_data

    async def _async_save_stored_data(self) -> None:
        """Save stored data to disk."""
        if self._stored_data is not None:
            await self.store.async_save(self._stored_data)

    def _get_current_date(self) -> str:
        """Get current date string."""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_current_month(self) -> str:
        """Get current month string."""
        return datetime.now().strftime("%Y-%m")

    def _parse_create_time(self, order: dict) -> datetime | None:
        """Parse createTime field (ISO format like '2026-01-10T06:52:17.000+00:00').
        
        The API returns UTC time, we need to convert to local time for comparison.
        """
        create_time_str = order.get("createTime", "")
        if create_time_str:
            try:
                # Parse ISO format - handle various formats
                # Remove milliseconds for simpler parsing
                clean_str = create_time_str
                if "." in clean_str:
                    # Split at . and keep the timezone part
                    parts = clean_str.split(".")
                    base = parts[0]
                    # Find timezone in the second part
                    tz_part = ""
                    if "+" in parts[1]:
                        tz_part = "+" + parts[1].split("+")[1]
                    elif "-" in parts[1]:
                        tz_part = "-" + parts[1].split("-")[1]
                    clean_str = base + tz_part
                
                # Try parsing with timezone
                if "+00:00" in clean_str or "Z" in clean_str:
                    clean_str = clean_str.replace("Z", "+00:00")
                    # Parse UTC time and convert to local time
                    dt_utc = datetime.fromisoformat(clean_str)
                    # Convert to local time by adding 8 hours (Beijing timezone)
                    # This is a simple fix; for production, consider using proper timezone handling
                    dt_local = dt_utc.replace(tzinfo=None) + timedelta(hours=8)
                    _LOGGER.debug(
                        "Converted order time from UTC %s to local %s",
                        clean_str,
                        dt_local.isoformat(),
                    )
                    return dt_local
                else:
                    # No timezone, parse as local time
                    dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S")
                    return dt
            except ValueError as e:
                _LOGGER.warning("Failed to parse createTime '%s': %s", create_time_str, e)
        return None

    def _process_orders_after_time(
        self,
        orders: list[dict],
        start_time: str,
        processed_ids: list[int],
    ) -> tuple[float, list[int]]:
        """Process orders that occurred after start_time."""
        total_recharge = 0.0
        new_processed_ids = processed_ids.copy()

        try:
            start_dt = datetime.fromisoformat(start_time)
            # Make sure start_dt is naive (no timezone)
            if start_dt.tzinfo is not None:
                start_dt = start_dt.replace(tzinfo=None)
        except ValueError:
            _LOGGER.warning("Invalid start_time format: %s", start_time)
            return 0.0, processed_ids

        for order in orders:
            order_id = order.get("orderId")
            order_dt = self._parse_create_time(order)
            
            if order_id is None or order_dt is None:
                continue
            
            # Make order_dt naive for comparison
            if order_dt.tzinfo is not None:
                order_dt_naive = order_dt.replace(tzinfo=None)
            else:
                order_dt_naive = order_dt
                
            # Only process orders that:
            # 1. Happened AFTER start_time
            # 2. Haven't been processed yet
            if order_dt_naive > start_dt and order_id not in processed_ids:
                try:
                    amount = float(order.get("numDesc", "0"))
                    total_recharge += amount
                    new_processed_ids.append(order_id)
                    _LOGGER.debug(
                        "Processed recharge order %s: %.2f CNY (time: %s)",
                        order_id,
                        amount,
                        order_dt.isoformat(),
                    )
                except (ValueError, TypeError):
                    _LOGGER.warning("Invalid order amount: %s", order.get("numDesc"))

        return total_recharge, new_processed_ids

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Load stored data
            stored_data = await self._async_load_stored_data()

            # Get gas data from API
            gas_data = await self.hass.async_add_executor_job(self.api.get_gas_data)

            if gas_data is None:
                raise UpdateFailed("Failed to fetch gas data")

            balance = gas_data.get("balance", 0)
            gas_price = gas_data.get("gas_price", 0)

            if balance is None or gas_price is None:
                raise UpdateFailed("Invalid gas data received")

            # Get order list from API
            orders = await self.hass.async_add_executor_job(self.api.get_order_list)
            orders = orders or []

            # Get current date and month
            current_date = self._get_current_date()
            current_month = self._get_current_month()
            now_iso = datetime.now().isoformat()

            # Initialize daily data if needed
            daily_data = stored_data.get("daily", {})
            if daily_data.get("date") != current_date:
                # New day - reset daily data with current time as start
                _LOGGER.info("New day detected, resetting daily data")
                daily_data = {
                    "date": current_date,
                    "start_time": now_iso,  # Track when we started
                    "start_balance": balance,
                    "recharge_total": 0.0,
                    "processed_order_ids": [],
                }

            # Initialize monthly data if needed
            monthly_data = stored_data.get("monthly", {})
            if monthly_data.get("month") != current_month:
                # New month - reset monthly data with current time as start
                _LOGGER.info("New month detected, resetting monthly data")
                monthly_data = {
                    "month": current_month,
                    "start_time": now_iso,  # Track when we started
                    "start_balance": balance,
                    "recharge_total": 0.0,
                    "processed_order_ids": [],
                }

            # Process orders for daily tracking (only orders AFTER daily start_time)
            daily_start_time = daily_data.get("start_time", now_iso)
            daily_recharge, daily_processed = self._process_orders_after_time(
                orders, daily_start_time, daily_data.get("processed_order_ids", [])
            )
            daily_data["recharge_total"] = daily_data.get("recharge_total", 0) + daily_recharge
            daily_data["processed_order_ids"] = daily_processed

            # Process orders for monthly tracking (only orders AFTER monthly start_time)
            monthly_start_time = monthly_data.get("start_time", now_iso)
            monthly_recharge, monthly_processed = self._process_orders_after_time(
                orders, monthly_start_time, monthly_data.get("processed_order_ids", [])
            )
            monthly_data["recharge_total"] = monthly_data.get("recharge_total", 0) + monthly_recharge
            monthly_data["processed_order_ids"] = monthly_processed

            # Calculate today's cost and usage
            # cost = start_balance - current_balance + recharges_since_start
            today_cost = max(
                0,
                daily_data.get("start_balance", balance)
                - balance
                + daily_data.get("recharge_total", 0),
            )
            today_usage = today_cost / gas_price if gas_price > 0 else 0

            # Calculate monthly cost and usage
            monthly_cost = max(
                0,
                monthly_data.get("start_balance", balance)
                - balance
                + monthly_data.get("recharge_total", 0),
            )
            monthly_usage = monthly_cost / gas_price if gas_price > 0 else 0

            # Get last recharge info
            last_recharge = None
            last_recharge_time = None
            if orders:
                last_order = orders[0]  # Most recent order
                try:
                    last_recharge = float(last_order.get("numDesc", "0"))
                    last_recharge_time = self._parse_create_time(last_order)
                except (ValueError, TypeError) as err:
                    _LOGGER.warning("Failed to parse last recharge info: %s", err)

            # Update stored data
            self._stored_data = {
                "daily": daily_data,
                "monthly": monthly_data,
                "last_balance": balance,
                "last_update": now_iso,
                "_minor_version": STORAGE_MINOR_VERSION,
            }
            await self._async_save_stored_data()

            # Return data for sensors
            return {
                "balance": balance,
                "gas_price": gas_price,
                "today_cost": round(today_cost, 2),
                "today_usage": round(today_usage, 3),
                "monthly_cost": round(monthly_cost, 2),
                "monthly_usage": round(monthly_usage, 3),
                "last_recharge": last_recharge,
                "last_recharge_time": last_recharge_time,
            }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
