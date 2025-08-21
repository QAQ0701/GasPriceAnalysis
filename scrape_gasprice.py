import asyncio
import logging
import random
from gasbuddy import GasBuddy
import pandas as pd
from datetime import datetime

# ------------------- CONFIG -------------------
LOCATIONS = [
    (49.249, -123.173),  # Vancouver West
    (49.243, -123.0823),  # Vancouver East
    (49.173, -123.079),  # Richmond East
    (49.15, -123.159),  # Richmond West
    (49.337039, -123.157945),  # West Vancouver
    (49.326, -123.073),  # North Vancouver
    (49.266048, -122.962936),  # Burnaby North
    (49.22, -122.96),  # Burnaby South
]
ZIP_CODES = ["V6M 3V2", "V6M 2V6", "V6P 2Z2", "V6X 3Z9"]
COOKIE_FILE = "./data/cookies/my_cookies.json"
LOG_FILE = "./log/debug_log.txt"
EXCEL_FILE = "./data/gas_prices.xlsx"
MIN_DELAY = 4
MAX_DELAY = 9
MAX_CONCURRENT = 1  # maximum concurrent requests

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",
)

# ------------------- GASBUDDY INSTANCE -------------------
gb = GasBuddy(cookie_file=COOKIE_FILE)  # single instance for all queries
semaphore = asyncio.Semaphore(MAX_CONCURRENT)  # control concurrency


# ------------------- ASYNC FETCH -------------------
async def fetch_station_prices(station_id: str) -> dict:
    async with semaphore:
        gb._id = station_id
        try:
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            result = await gb.price_lookup()
            logging.debug(f"Fetched_station_prices {station_id}: {result}")
            if not isinstance(result, dict):
                return {"error": "No data"}
            return result
        except Exception as e:
            logging.error(f"Failed fetching station {station_id}: {e}")
            return {"error": str(e)}


async def search_stations_by_coords(lat: float, lon: float) -> dict:
    """Return all nearby stations given latitude and longitude."""
    async with semaphore:
        try:
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            logging.info(f"Searching stations by coordinates ({lat},{lon})")
            return await gb.location_search(lat=lat, lon=lon)
        except Exception as e:
            logging.error(f"Error searching by coordinates ({lat},{lon}): {e}")
            return {"error": str(e)}


async def search_stations_by_zip(zip_code: str) -> dict:
    """Return stations for a given postal code."""
    async with semaphore:
        try:
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            return await gb.location_search(zipcode=zip_code)
        except Exception as e:
            logging.error(f"Error searching by zip code {zip_code}: {e}")
            return {"error": str(e)}


# ------------------- PARSE RESPONSE -------------------
async def parse_gas_stations(response: dict):
    """Parse raw response from GasBuddy into structured station data with debug logging."""
    if not isinstance(response, dict):
        logging.error("Invalid response: not a dict")
        logging.error(
            f"parse_gas_stations: Unexpected response type: {type(response)}, value: {response}"
        )
        return []

    if response.get("error"):
        logging.error(
            f"parse_gas_stations: Response contains error: {response.get('error')}"
        )
        return []

    logging.debug(f"Raw response: {response}")
    data = response.get("data")
    logging.debug(f"data: {data}")
    loc = data.get("locationBySearchTerm") if data else None
    logging.debug(f"locationBySearchTerm: {loc}")
    stations_obj = loc.get("stations") if loc else None
    logging.debug(f"stations object: {stations_obj}")
    stations = stations_obj.get("results") if stations_obj else []
    logging.debug(f"stations list: {stations}")

    if not stations:
        logging.warning("parse_gas_stations: No stations found in response")
        return []

    # Fetch prices with concurrency control
    tasks = [fetch_station_prices(st.get("id")) for st in stations if st]
    logging.info(f"Fetching prices for {len(stations)} stations")
    prices_list = await asyncio.gather(*tasks)

    parsed_results = []
    for st, prices in zip(stations, prices_list):
        logging.debug(f"Station loop raw: {st}, prices raw: {prices}")
        st = st or {}
        prices = prices or {}

        if not st.get("id") or not st.get("name"):
            logging.warning(f"Station missing ID or name: {st}")
        if not prices:
            logging.warning(f"Prices missing for station {st.get('id')}: {prices}")

        parsed_results.append(
            {
                "Station ID": st.get("id"),
                "Station Name": st.get("name"),
                "Address": (st.get("address") or {}).get("line1"),
                "Location": {
                    "Latitude": prices.get("latitude"),
                    "Longitude": prices.get("longitude"),
                },
                "Unit of Measure": prices.get("unit_of_measure"),
                "Currency": prices.get("currency"),
                "Image URL": prices.get("image_url"),
                "Regular Gas": prices.get("regular_gas"),
                "Premium Gas": prices.get("premium_gas"),
            }
        )
    logging.info("Exited loop")

    return parsed_results


# ------------------- SAVE TO EXCEL -------------------
def save_prices_to_excel(data: list[dict], filename: str = EXCEL_FILE):
    """Append gas station data to Excel, avoiding duplicates, safely handling None values."""
    try:
        existing = pd.read_excel(filename)
    except FileNotFoundError:
        existing = pd.DataFrame(
            columns=[
                "Station ID",
                "Station Name",
                "Address",
                "Location",
                "Query Time",
                "Regular Last Update Time",
                "Regular Price",
                "Premium Last Update Time",
                "Premium Price",
            ]
        )
    query_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_rows = []
    logging.info(f"Saving {len(data)} rows to {filename}")

    for idx, st in enumerate(data):
        if not isinstance(st, dict):
            logging.warning(f"Skipping invalid station data at index {idx}: {st}")
            continue

        # Safely get gas price info
        regular = st.get("Regular Gas") or {}
        premium = st.get("Premium Gas") or {}

        new_row = {
            "Station ID": st.get("Station ID"),
            "Station Name": st.get("Station Name"),
            "Address": st.get("Address"),
            "Location": st.get("Location"),
            "Query Time": query_time,
            "Regular Last Update Time": regular.get("last_updated"),
            "Regular Price": regular.get("price"),
            "Premium Last Update Time": premium.get("last_updated"),
            "Premium Price": premium.get("price"),
        }

        # Log missing prices
        if not regular:
            logging.debug(
                f"Missing regular gas info for station {st.get('Station ID')}"
            )
        if not premium:
            logging.debug(
                f"Missing premium gas info for station {st.get('Station ID')}"
            )

        # Avoid duplicates
        duplicate = existing[
            (existing["Station ID"] == new_row["Station ID"])
            & (existing["Query Time"] == new_row["Query Time"])
        ]
        if duplicate.empty:
            new_rows.append(new_row)

    if new_rows:
        updated = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        updated.to_excel(filename, index=False)
        logging.info(f"Saved {len(new_rows)} new rows to {filename}")
    else:
        logging.info("No new data to save.")


# ------------------- MAIN FETCH -------------------
async def fetch_all_locations_and_zips():
    """Fetch and save prices for all locations and zip codes."""
    for lat, lon in LOCATIONS:
        print(lat, lon)
        logging.info(f"Fetching stations for ({lat},{lon})")
        response = await search_stations_by_coords(lat, lon)
        data = await parse_gas_stations(response)
        save_prices_to_excel(data)
        await asyncio.sleep(5)

    # for zip_code in ZIP_CODES:
    #     logging.info(f"Fetching stations for zip code {zip_code}")
    #     response = await search_stations_by_zip(zip_code)
    #     data = await parse_gas_stations(response)
    #     save_prices_to_excel(data)


def main():
    try:
        asyncio.run(fetch_all_locations_and_zips())
    except Exception as e:
        logging.error(f"Error in main: {e}")


if __name__ == "__main__":
    main()
    # async def test():
    #     gb = GasBuddy()
    #     gb._load_cookies("data/cookies/my_cookies.json")
    #     result = await gb.location_search(lat=49.249, lon=-123.173)
    #     print(result)

    # asyncio.run(test())
