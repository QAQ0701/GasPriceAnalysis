from __future__ import annotations
import json
import logging
from typing import Any, Collection
import aiohttp
import backoff

from .consts import BASE_URL, GAS_PRICE_QUERY, LOCATION_QUERY, LOCATION_QUERY_PRICES
from .exceptions import APIError, LibraryError, MissingSearchData

_LOGGER = logging.getLogger(__name__)
MAX_RETRIES = 5

class GasBuddy:
    """Represents GasBuddy GraphQL calls using saved cookies + gbcsrf token."""

    def __init__(self, station_id: int | None = None, cookie_file: str | None = None) -> None:
        self._url = BASE_URL
        self._id = station_id
        self._tag = None  # gbcsrf token
        self.cookie_jar = {}
        
        if cookie_file:
            self._load_cookies(cookie_file)

    def _load_cookies(self, path: str) -> None:
        """Load cookies and gbcsrf token from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.cookie_jar = {c["name"]: c["value"] for c in data.get("cookies", [])}
        self._tag = data.get("gbcsrf")
        if self._tag:
            _LOGGER.debug("Loaded gbcsrf token from JSON.")

    def _build_headers(self) -> dict[str, str]:
        """Return Chrome-like headers with gbcsrf token included."""
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "Origin": "https://www.gasbuddy.com",
            "Referer": "https://www.gasbuddy.com/home",
            "apollo-require-preflight": "true",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            **({"gbcsrf": self._tag} if self._tag else {})
        }

    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_time=60, max_tries=MAX_RETRIES)
    async def process_request(self, query: dict[str, Collection[str]]) -> dict[str, Any]:
        """Send GraphQL query with saved cookies and gbcsrf token."""
        headers = self._build_headers()
        json_query = json.dumps(query)

        async with aiohttp.ClientSession(headers=headers, cookies=self.cookie_jar) as session:
            async with session.post(self._url, data=json_query) as response:
                text = await response.text()
                try:
                    message = json.loads(text)
                except ValueError:
                    message = {"error": text}

                if response.status == 403:
                    _LOGGER.error("403 Forbidden — Cloudflare blocked request.")
                elif response.status != 200:
                    _LOGGER.error("HTTP %s: %s", response.status, message)
                return message

    async def location_search(self, lat: float | None = None, lon: float | None = None, zipcode: int | None = None) -> dict[str, Any]:
        """Search locations using coordinates or zipcode."""
        variables: dict[str, Any] = {}
        if lat is not None and lon is not None:
            variables = {"maxAge": 0, "lat": lat, "lng": lon}
        elif zipcode is not None:
            variables = {"maxAge": 0, "search": str(zipcode)}
        else:
            _LOGGER.error("Missing search data.")
            raise MissingSearchData

        query = {
            "operationName": "LocationBySearchTerm",
            "query": LOCATION_QUERY,
            "variables": variables,
        }
        return await self.process_request(query)

    async def price_lookup(self) -> dict[str, Any] | None:
        """Return gas price for a specific station."""
        logging.info(f"price_lookup for station {self._id}")
        if not self._id:
            raise ValueError("station_id must be set for price_lookup.")

        query = {
            "operationName": "GetStation",
            "query": GAS_PRICE_QUERY,
            "variables": {"id": str(self._id)},
        }

        response = await self.process_request(query)
        if "error" in response:
            _LOGGER.error("Error fetching station: %s", response["error"])
            raise LibraryError
        if "errors" in response:
            message = response["errors"][0].get("message", "Server-side error")
            _LOGGER.error("API Error: %s", message)
            raise APIError

        data = response["data"]["station"]
        # Format results as needed
        formatted = {
            "station_id": data["id"],
            "unit_of_measure": data["priceUnit"],
            "currency": data["currency"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "image_url": data["brands"][0]["imageUrl"] if data["brands"] else None,
        }

        # Prices
        for price in data["prices"]:
            index = price["fuelProduct"]
            formatted[index] = {
                "credit": price["credit"]["nickname"],
                "price": price["credit"].get("price"),
                "cash_price": price.get("cash", {}).get("price") if price.get("cash") else None,
                "last_updated": price["credit"]["postedTime"],
            }
        logging.info(f"Saved {formatted} for station {self._id}")
        return formatted
