"""API client for Xinao Energy Analysis."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

import requests

from .const import API_URL, API_SECRET, DEFAULT_CLIENT_TYPE

_LOGGER = logging.getLogger(__name__)


class XinaoEnergyAPI:
    """API client for Xinao Energy."""

    def __init__(self, token: str, payment_no: str, company_code: str) -> None:
        """Initialize the API client."""
        self.token = token
        self.payment_no = payment_no
        self.company_code = company_code
        self.client_type = DEFAULT_CLIENT_TYPE

    def generate_app_key(self) -> str:
        """Generate appKey for API request."""
        now = datetime.now()
        time_str = now.strftime("%Y%m%d%H%M%S")
        sign_str = time_str + API_SECRET
        md5_hash = hashlib.md5(sign_str.encode("utf-8")).hexdigest()
        app_key = time_str + md5_hash
        return app_key

    def get_energy_analysis(self) -> dict[str, Any] | None:
        """Get energy analysis data."""
        url = API_URL

        headers = {
            "Host": "wechatapp.ecej.com",
            "Connection": "keep-alive",
            "token": self.token,
            "content-type": "application/x-www-form-urlencoded",
            "token-type": "2",
            "Accept-Encoding": "gzip,compress,br,deflate",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.53(0x18003531) NetType/4G Language/zh_CN",
            "Referer": "https://servicewechat.com/wxd722317df8c566fe/224/page-frame.html",
        }

        data = {
            "appKey": self.generate_app_key(),
            "token": self.token,
            "clientType": self.client_type,
            "paymentNo": self.payment_no,
            "companyCode": self.company_code,
        }

        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()

            json_data = response.json()

            if json_data.get("resultCode") == 200:
                _LOGGER.debug("Successfully fetched energy analysis data")
                return json_data
            else:
                _LOGGER.error(
                    "API returned error: %s - %s",
                    json_data.get("resultCode"),
                    json_data.get("message"),
                )
                return None

        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to fetch energy analysis data: %s", err)
            return None
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            return None
