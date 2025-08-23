import asyncio
import aiohttp
import json
import time
import csv
import pytz
from datetime import datetime
import re

# import pandas as pd
# import matplotlib.pyplot as plt

LOCATION_QUERY_PRICES = "query LocationBySearchTerm($brandId: Int, $cursor: String, $fuel: Int, $lat: Float, $lng: Float, $maxAge: Int, $search: String) { locationBySearchTerm(lat: $lat, lng: $lng, search: $search) { stations(brandId: $brandId cursor: $cursor fuel: $fuel lat: $lat lng: $lng maxAge: $maxAge) { results { address { line1 } name prices { cash { nickname postedTime price } credit { nickname postedTime price } fuelProduct longName } priceUnit currency id latitude longitude } } trends { areaName country today todayLow trend } } }"

# --- Helper to load cookies ---
COOKIE_FILE = "data/cookies/my_cookies.json"  # <- your cookie dump file
# LOG_FILE = "log/rate_limit_log.csv"


def load_cookies_from_file(cookie_file):
    with open(cookie_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        cookies = {c["name"]: c["value"] for c in data.get("cookies", [])}
        token = data.get("gbcsrf")
    return cookies, token


COOKIES, TOKEN = load_cookies_from_file(COOKIE_FILE)

# --- SETTINGS ---
GRAPHQL_URL = "https://www.gasbuddy.com/graphql"
HEADERS = {
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
    **({"gbcsrf": TOKEN} if TOKEN else {}),
}

# print(HEADERS)
# 49.249, -123.173
TEST_QUERY = {
    "operationName": "LocationBySearchTerm",
    "query": LOCATION_QUERY_PRICES,
    "variables": {
        "brandId": None,
        "cursor": None,
        "fuel": None,
        "lat": 49.249,
        "lng": -123.173,
        "maxAge": 0,
        "search": None,
    },
}


# --- Request function ---
async def send_request(session, idx, delay, success_count):
    try:
        async with session.post(GRAPHQL_URL, data=json.dumps(TEST_QUERY)) as resp:
            text = await resp.text()
            if resp.status == 200:
                print(f"[{idx}] OK")
                # Parse JSON and print the 'data' field
                try:
                    response_json = json.loads(text)
                    data = response_json.get("data")
                    print(f"[{idx}] Response data:", json.dumps(data, indent=2))
                    return data
                except json.JSONDecodeError:
                    print(f"[{idx}] Failed to parse JSON")
                return True
            else:
                print(f"[{idx}] BLOCKED {resp.status} {text[:80]}")
                return False
    except Exception as e:
        print(f"[{idx}] ERROR: {e}")
        return False


def parse_response(response_json):
    """
    Parses a GasBuddy GraphQL response into a list of dictionaries.

    Args:
        response_json (dict): The JSON response from the API.

    Returns:
        list of dict: Each dict contains station info and prices.
    """
    parsed_stations = []

    stations = (
        response_json.get("locationBySearchTerm", {})
        .get("stations", {})
        .get("results", [])
    )

    for station in stations:
        station_dict = {
            "address": station.get("address", {}).get("line1"),
            "prices": [],
            "priceUnit": station.get("priceUnit"),
            "currency": station.get("currency"),
            "id": station.get("id"),
            "latitude": station.get("latitude"),
            "longitude": station.get("longitude"),
        }

        for price_entry in station.get("prices", []):
            # Extract cash and credit prices if available
            cash_info = price_entry.get("cash")
            credit_info = price_entry.get("credit")

            price_dict = {
                "fuelProduct": price_entry.get("fuelProduct"),
                "longName": price_entry.get("longName"),
                "cash_price": cash_info.get("price") if cash_info else None,
                "cash_time": cash_info.get("postedTime") if cash_info else None,
                "credit_price": credit_info.get("price") if credit_info else None,
                "credit_time": credit_info.get("postedTime") if credit_info else None,
            }

            station_dict["prices"].append(price_dict)

        parsed_stations.append(station_dict)

    return parsed_stations


async def main():

    async with aiohttp.ClientSession(headers=HEADERS, cookies=COOKIES) as session:
        delay = 5.0  # start slow
        idx = 0
        success_count = 0
        idx += 1
        data = await send_request(session, idx, delay, success_count)
        results = parse_response(data)
        # print(results)
        print(results[0].get("address"))
        print(results[0].get("prices"))
        print(results[0].get("priceUnit"))
        print(results[0].get("currency"))
        print(results[0].get("id"))
        print(results[0].get("latitude"))
        print(results[0].get("longitude"))


def group_prices(data):
    fuel_groups = {"Regular": {}, "Midgrade": {}, "Premium": {}, "Diesel": {}}
    for entry in data:
        long_name = entry.get("longName")
        if long_name in fuel_groups:
            fuel_groups[long_name] = entry
    return (
        fuel_groups["Regular"],
        fuel_groups["Midgrade"],
        fuel_groups["Premium"],
        fuel_groups["Diesel"],
    )


test_data = [
    {
        "fuelProduct": "regular_gas",
        "longName": "Regular",
        "cash_price": None,
        "cash_time": None,
        "credit_price": 161.9,
        "credit_time": "2025-08-22T03:03:56.105Z",
    },
    {
        "fuelProduct": "midgrade_gas",
        "longName": "Midgrade",
        "cash_price": None,
        "cash_time": None,
        "credit_price": 180.9,
        "credit_time": "2025-08-21T05:37:56.501Z",
    },
    {
        "fuelProduct": "premium_gas",
        "longName": "Premium",
        "cash_price": None,
        "cash_time": None,
        "credit_price": 188.9,
        "credit_time": "2025-08-21T05:37:56.532Z",
    },
]


def iso_to_pdt(utc_time):
    """Convert UTC time to PST (Pacific Standard Time)."""
    utc_dt = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    pdt_dt = utc_dt.astimezone(pytz.timezone("America/Los_Angeles"))
    print("UTC:", utc_dt, "PST:", pdt_dt)
    return pdt_dt


def is_iso_string(s: str) -> bool:
    ISO_UTC_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
    if not isinstance(s, str):
            return False
    return bool(ISO_UTC_REGEX.match(s))


if __name__ == "__main__":
    # asyncio.run(main())

    print(is_iso_string("2025-08-19T00:51:31.164Z"))
    print(is_iso_string("2025-08-23 04:11:39"))

    """
    # regular, midgrade, premium, diesel = group_prices(test_data)
    # print("Regular:", regular)
    # print("Midgrade:", midgrade)
    # print("Premium:", premium)
    # print("Diesel:", diesel)
    # rt = iso_to_pdt(regular["credit_time"] or regular["cash_time"]) if regular else None
    # pt = iso_to_pdt(premium["credit_time"] or premium["cash_time"]) if premium else None
    # mt = (
    #     iso_to_pdt(midgrade["credit_time"] or midgrade["cash_time"])
    #     if midgrade
    #     else None
    # )
    # dt = iso_to_pdt(diesel["credit_time"] or diesel["cash_time"]) if diesel else None
    # print("Regular Time:", rt)
    # rt = iso_to_pdt(regular["credit_time"] or regular["cash_time"])
    # reg_price = regular["credit_price"] or regular["cash_price"]
    # print("Regular Price:", reg_price, "Regular Time:", rt)
    """

"""
{
    "data": {
        "locationBySearchTerm": {
            "stations": {
                "results": [
                    {
                        "address": {"line1": "3250 MacDonald St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "shockstorm",
                                    "postedTime": "2025-08-23T00:06:51.343Z",
                                    "price": 159.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "shockstorm",
                                    "postedTime": "2025-08-21T05:37:56.501Z",
                                    "price": 180.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "shockstorm",
                                    "postedTime": "2025-08-21T05:37:56.532Z",
                                    "price": 188.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65542",
                        "latitude": 49.2573819,
                        "longitude": -123.1680407,
                    },
                    {
                        "address": {"line1": "4615 Arbutus St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "alukips",
                                    "postedTime": "2025-08-22T22:34:44.074Z",
                                    "price": 159,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "TeoDav123",
                                    "postedTime": "2025-08-23T00:26:37.749Z",
                                    "price": 180.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "TeoDav123",
                                    "postedTime": "2025-08-23T00:26:37.765Z",
                                    "price": 188.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65533",
                        "latitude": 49.2449719,
                        "longitude": -123.1540385,
                    },
                    {
                        "address": {"line1": "3205 Arbutus St"},
                        "prices": [],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "83068",
                        "latitude": 49.256927568207,
                        "longitude": -123.153288960457,
                    },
                    {
                        "address": {"line1": "2808 W Broadway"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T23:08:08.216Z",
                                    "price": 160.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T23:08:08.216Z",
                                    "price": 177.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T23:08:08.232Z",
                                    "price": 185.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65562",
                        "latitude": 49.263883932125,
                        "longitude": -123.168604373932,
                    },
                    {
                        "address": {"line1": "3596 W 41st Ave"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "2012ml",
                                    "postedTime": "2025-08-22T23:15:35.442Z",
                                    "price": 167.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Buddy_8yk9z7yz",
                                    "postedTime": "2025-08-21T22:45:28.845Z",
                                    "price": 189.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Buddy_8yk9z7yz",
                                    "postedTime": "2025-08-21T22:45:28.860Z",
                                    "price": 194.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "113305",
                        "latitude": 49.234385296079,
                        "longitude": -123.184762001038,
                    },
                    {
                        "address": {"line1": "2103 W Broadway"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Anne5345",
                                    "postedTime": "2025-08-22T23:39:44.680Z",
                                    "price": 161.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Anne5345",
                                    "postedTime": "2025-08-22T23:39:44.703Z",
                                    "price": 186.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Anne5345",
                                    "postedTime": "2025-08-22T23:39:44.719Z",
                                    "price": 191.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "2012ml",
                                    "postedTime": "2025-08-22T23:17:45.551Z",
                                    "price": 180.9,
                                },
                                "fuelProduct": "diesel",
                                "longName": "Diesel",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65570",
                        "latitude": 49.264135981257,
                        "longitude": -123.153326511383,
                    },
                    {
                        "address": {"line1": "1795 W Broadway"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "renegade_mami",
                                    "postedTime": "2025-08-22T21:53:57.315Z",
                                    "price": 161.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "shopbuddy11",
                                    "postedTime": "2025-08-22T20:03:26.681Z",
                                    "price": 181.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "shopbuddy11",
                                    "postedTime": "2025-08-22T20:03:26.696Z",
                                    "price": 188.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65554",
                        "latitude": 49.264037962303,
                        "longitude": -123.145408630371,
                    },
                    {
                        "address": {"line1": "4314 W 10th Ave"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T22:58:37.461Z",
                                    "price": 167.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T22:58:37.461Z",
                                    "price": 192.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T22:58:37.477Z",
                                    "price": 197.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T22:58:37.493Z",
                                    "price": 180.9,
                                },
                                "fuelProduct": "diesel",
                                "longName": "Diesel",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65571",
                        "latitude": 49.263533861752,
                        "longitude": -123.203430175781,
                    },
                    {
                        "address": {"line1": "1896 W 4th Ave"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "milomixer",
                                    "postedTime": "2025-08-23T01:05:23.856Z",
                                    "price": 157.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": None,
                                    "postedTime": None,
                                    "price": 0,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": None,
                                    "postedTime": None,
                                    "price": 0,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65565",
                        "latitude": 49.267881559667,
                        "longitude": -123.14772605896,
                    },
                    {
                        "address": {"line1": "1503 W 41st Ave"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "2012ml",
                                    "postedTime": "2025-08-22T23:13:42.533Z",
                                    "price": 167.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "jhlin",
                                    "postedTime": "2025-08-22T05:23:30.088Z",
                                    "price": 184.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "32376",
                        "latitude": 49.234634576953,
                        "longitude": -123.139971792698,
                    },
                    {
                        "address": {"line1": "5702 Granville St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "federico2011",
                                    "postedTime": "2025-08-22T19:02:06.046Z",
                                    "price": 169.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "harmanpreetinfo",
                                    "postedTime": "2025-08-22T00:05:40.484Z",
                                    "price": 178.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "harmanpreetinfo",
                                    "postedTime": "2025-08-22T00:05:40.501Z",
                                    "price": 196.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65549",
                        "latitude": 49.234036184118,
                        "longitude": -123.139244914055,
                    },
                    {
                        "address": {"line1": "1900 Burrard St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "milomixer",
                                    "postedTime": "2025-08-23T01:05:18.605Z",
                                    "price": 157.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "smjmtyvr",
                                    "postedTime": "2025-08-21T19:46:17.778Z",
                                    "price": 181.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "smjmtyvr",
                                    "postedTime": "2025-08-21T19:46:17.794Z",
                                    "price": 194.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "sbliss68",
                                    "postedTime": "2025-08-23T00:47:43.915Z",
                                    "price": 178.9,
                                },
                                "fuelProduct": "diesel",
                                "longName": "Diesel",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65543",
                        "latitude": 49.2685375,
                        "longitude": -123.1453067,
                    },
                    {
                        "address": {"line1": "1743 Burrard St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "milomixer",
                                    "postedTime": "2025-08-23T01:05:34.430Z",
                                    "price": 157.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": None,
                                    "postedTime": None,
                                    "price": 0,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "ecps92",
                                    "postedTime": "2025-08-22T21:26:38.260Z",
                                    "price": 184.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65563",
                        "latitude": 49.270429790667,
                        "longitude": -123.145886063576,
                    },
                    {
                        "address": {"line1": "1010 W King Edward Ave"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "2crazy",
                                    "postedTime": "2025-08-23T00:47:51.938Z",
                                    "price": 162.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "bcdude777",
                                    "postedTime": "2025-08-22T22:11:40.241Z",
                                    "price": 185.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "bcdude777",
                                    "postedTime": "2025-08-22T22:11:16.169Z",
                                    "price": 193.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "namron",
                                    "postedTime": "2025-08-22T22:16:18.544Z",
                                    "price": 178.9,
                                },
                                "fuelProduct": "diesel",
                                "longName": "Diesel",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "72747",
                        "latitude": 49.249188,
                        "longitude": -123.127767,
                    },
                    {
                        "address": {"line1": "4110 Oak St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "2crazy",
                                    "postedTime": "2025-08-23T00:47:56.633Z",
                                    "price": 162.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "milomixer",
                                    "postedTime": "2025-08-22T06:29:37.293Z",
                                    "price": 180.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "milomixer",
                                    "postedTime": "2025-08-22T06:29:37.309Z",
                                    "price": 185.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "32375",
                        "latitude": 49.24894071957,
                        "longitude": -123.127040863037,
                    },
                    {
                        "address": {"line1": "5680 Oak St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Buddy_995nakrd",
                                    "postedTime": "2025-08-22T22:30:58.767Z",
                                    "price": 162.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Usha1126",
                                    "postedTime": "2025-08-22T15:18:22.520Z",
                                    "price": 179.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Usha1126",
                                    "postedTime": "2025-08-22T15:18:22.536Z",
                                    "price": 187.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65564",
                        "latitude": 49.234217162181,
                        "longitude": -123.127684593201,
                    },
                    {
                        "address": {"line1": "6525 Oak St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Buddy_995nakrd",
                                    "postedTime": "2025-08-22T22:32:22.799Z",
                                    "price": 165.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Usha1126",
                                    "postedTime": "2025-08-22T15:18:58.129Z",
                                    "price": 180.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "Usha1126",
                                    "postedTime": "2025-08-22T15:18:58.145Z",
                                    "price": 188.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "32372",
                        "latitude": 49.226226639452,
                        "longitude": -123.128687739372,
                    },
                    {
                        "address": {"line1": "1205 Burrard St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "sbliss68",
                                    "postedTime": "2025-08-23T00:51:28.169Z",
                                    "price": 159.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T23:27:11.450Z",
                                    "price": 181.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "MrxAtheist",
                                    "postedTime": "2025-08-22T23:27:11.466Z",
                                    "price": 192.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "9707",
                        "latitude": 49.279145231489,
                        "longitude": -123.12982365489,
                    },
                    {
                        "address": {"line1": "8072 Granville St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "meetgaidu",
                                    "postedTime": "2025-08-22T22:30:51.959Z",
                                    "price": 168.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": None,
                                    "postedTime": None,
                                    "price": 0,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": None,
                                    "postedTime": None,
                                    "price": 0,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": None,
                                    "postedTime": None,
                                    "price": 0,
                                },
                                "fuelProduct": "diesel",
                                "longName": "Diesel",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65566",
                        "latitude": 49.212495055855,
                        "longitude": -123.14013004303,
                    },
                    {
                        "address": {"line1": "8686 Granville St"},
                        "prices": [
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "pchanhf",
                                    "postedTime": "2025-08-22T20:24:40.907Z",
                                    "price": 169.9,
                                },
                                "fuelProduct": "regular_gas",
                                "longName": "Regular",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "ysrael04",
                                    "postedTime": "2025-08-21T21:50:22.584Z",
                                    "price": 190.9,
                                },
                                "fuelProduct": "midgrade_gas",
                                "longName": "Midgrade",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "ysrael04",
                                    "postedTime": "2025-08-21T21:50:22.600Z",
                                    "price": 195.9,
                                },
                                "fuelProduct": "premium_gas",
                                "longName": "Premium",
                            },
                            {
                                "cash": None,
                                "credit": {
                                    "nickname": "773450553",
                                    "postedTime": "2025-08-22T20:04:00.861Z",
                                    "price": 180.9,
                                },
                                "fuelProduct": "diesel",
                                "longName": "Diesel",
                            },
                        ],
                        "priceUnit": "cents_per_liter",
                        "currency": "CAD",
                        "id": "65572",
                        "latitude": 49.207280329467,
                        "longitude": -123.140280246735,
                    },
                ]
            },
            "trends": [
                {
                    "areaName": "Vancouver",
                    "country": "CA",
                    "today": 165.6,
                    "todayLow": 134.9,
                    "trend": 1,
                },
                {
                    "areaName": "British Columbia",
                    "country": "CA",
                    "today": 157.4,
                    "todayLow": 130.9,
                    "trend": 1,
                },
                {
                    "areaName": "Canada",
                    "country": "CA",
                    "today": 137.6,
                    "todayLow": 0,
                    "trend": 1,
                },
            ],
        }
    }
}
"""
