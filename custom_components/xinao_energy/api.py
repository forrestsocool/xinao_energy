"""API client for Xinao Energy."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Callable

import requests

from .const import API_URL, TOKEN_REFRESH_URL, ORDER_LIST_URL, API_SECRET

_LOGGER = logging.getLogger(__name__)


class XinaoEnergyAPI:
    """API client for Xinao Energy."""

    def __init__(self, token: str, device_id: str, city_id: str = "62") -> None:
        """Initialize the API client."""
        self.token = token
        self.device_id = device_id
        self.city_id = city_id
        self._token_refresh_callback: Callable[[str], None] | None = None

    def set_token_refresh_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback to be called when token is refreshed."""
        self._token_refresh_callback = callback

    def generate_app_key(self) -> str:
        """Generate appKey with timestamp and MD5 signature."""
        now = datetime.now()
        time_str = now.strftime("%Y%m%d%H%M%S")
        sign_str = time_str + API_SECRET
        md5_hash = hashlib.md5(sign_str.encode("utf-8")).hexdigest()
        app_key = time_str + md5_hash.upper()
        return app_key

    def refresh_token(self) -> str | None:
        """Refresh the token and return new token."""
        url = TOKEN_REFRESH_URL

        headers = {
            "Host": "ucapi.ecej.com",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "ECEJ/6.5.9 (com.ecej.ECEJ; build:101383; iOS 14.8.0) Alamofire/4.9.1",
            "platform": "ios",
            "cityId": self.city_id,
        }

        data = {
            "appKey": self.generate_app_key(),
            "cityId": self.city_id,
            "token": self.token,
        }

        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()

            json_data = response.json()
            _LOGGER.debug("Token refresh response: %s", json_data)

            if json_data.get("resultCode") == 200:
                new_token = json_data.get("data", {}).get("token")
                if new_token:
                    self.token = new_token
                    _LOGGER.info("Token refreshed successfully")
                    if self._token_refresh_callback:
                        self._token_refresh_callback(new_token)
                    return new_token
            else:
                _LOGGER.error(
                    "Token refresh failed: %s - %s",
                    json_data.get("resultCode"),
                    json_data.get("message"),
                )
                return None

        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to refresh token: %s", err)
            return None

    def get_gas_data(self, retry_on_401: bool = True) -> dict[str, Any] | None:
        """Get gas meter data (balance, gasPrice)."""
        url = API_URL

        headers = {
            "Content-Type": "application/json",
            "Origin": "https://iot.ecej.com",
            "withCredentials": "true",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148/ecejApp/6.4.5",
            "Authorization": f"Bearer {self.token}",
            "Host": "iot.ecej.com",
            "Accept": "application/json, text/plain, */*",
        }

        body = {
            "deviceId": self.device_id,
            "deviceType": "3",
            "appKey": self.generate_app_key(),
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)

            # Handle 401 - token expired
            if response.status_code == 401 and retry_on_401:
                _LOGGER.warning("Token expired, attempting to refresh...")
                new_token = self.refresh_token()
                if new_token:
                    # Retry with new token
                    return self.get_gas_data(retry_on_401=False)
                else:
                    _LOGGER.error("Failed to refresh token")
                    return None

            response.raise_for_status()

            json_data = response.json()
            _LOGGER.debug("Gas data response: %s", json_data)

            if json_data.get("code") == 200:
                data = json_data.get("data", {})
                return {
                    "balance": data.get("balance"),
                    "gas_price": data.get("gasPrice"),
                    "raw_data": data,
                }
            else:
                _LOGGER.error(
                    "API returned error: %s - %s",
                    json_data.get("code"),
                    json_data.get("message"),
                )
                return None

        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to fetch gas data: %s", err)
            return None

    def get_order_list(self, page_size: int = 10, retry_on_401: bool = True) -> list[dict] | None:
        """Get recharge order list."""
        url = ORDER_LIST_URL

        headers = {
            "Host": "oc.ecej.com",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ECEJ/6.5.9 (iPhone; iOS 14.8; Scale/2.00)",
            "platform": "ios",
            "cityId": self.city_id,
        }

        data = {
            "appKey": self.generate_app_key(),
            "orderStatus": "0",
            "pageNum": "1",
            "pageSize": str(page_size),
            "token": self.token,
            "type": "2",
            "version": "1",
        }

        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)

            # Handle 401 - token expired
            if response.status_code == 401 and retry_on_401:
                _LOGGER.warning("Token expired on order list, attempting to refresh...")
                new_token = self.refresh_token()
                if new_token:
                    return self.get_order_list(page_size=page_size, retry_on_401=False)
                else:
                    _LOGGER.error("Failed to refresh token")
                    return None

            response.raise_for_status()

            json_data = response.json()
            _LOGGER.debug("Order list response: %s", json_data)

            if json_data.get("resultCode") == 200:
                orders = json_data.get("data", [])
                # Filter only completed orders (orderStat == 3)
                completed_orders = [
                    order for order in orders if order.get("orderStat") == 3
                ]
                return completed_orders
            else:
                _LOGGER.error(
                    "Order list API error: %s - %s",
                    json_data.get("resultCode"),
                    json_data.get("message"),
                )
                return None

        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to fetch order list: %s", err)
            return None
