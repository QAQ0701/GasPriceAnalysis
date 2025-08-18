import asyncio
import logging
from gasbuddy import GasBuddy
import pandas as pd
from datetime import datetime

# ------------------- CONFIG -------------------
LOCATIONS = [(49.243, -123.0823), (49.173, -123.079), (49.15, -123.159)]
ZIP_CODES = ["V6M 3V2", "V6M 2V6", "V6P 2Z2", "V6X 3Z9"]
COOKIE_FILE = "./data/cookies/my_cookies.json"
LOG_FILE = "./log/debug_log.txt"
EXCEL_FILE = "./data/gas_prices.xlsx"

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",
)

# ------------------- GASBUDDY INSTANCE -------------------
gb = GasBuddy(cookie_file=COOKIE_FILE)  # Single instance for all queries

# ------------------- ASYNC FETCH -------------------
async def fetch_station_prices(station_id: str) -> dict:
    """Fetch price info for a single station."""
    try:
        return await gb.price_lookup(station_id=station_id)
    except Exception as e:
        logging.error(f"Failed fetching station {station_id}: {e}")
        return {"error": str(e)}

async def search_stations_by_coords(lat: float, lon: float) -> dict:
    """Return all nearby stations given latitude and longitude."""
    try:
        return await gb.location_search(lat=lat, lon=lon)
    except Exception as e:
        logging.error(f"Error searching by coordinates ({lat},{lon}): {e}")
        return {"error": str(e)}

async def search_stations_by_zip(zip_code: str) -> dict:
    """Return stations for a given postal code."""
    try:
        return await gb.location_search(zipcode=zip_code)
    except Exception as e:
        logging.error(f"Error searching by zip code {zip_code}: {e}")
        return {"error": str(e)}

# ------------------- PARSE RESPONSE -------------------
async def parse_gas_stations(response: dict):
    """Parse raw response from GasBuddy into structured station data."""
    if "error" in response:
        return []

    stations = response.get("data", {}).get("locationBySearchTerm", {}).get("stations", {}).get("results", [])
    if not stations:
        return []

    tasks = [fetch_station_prices(st.get("id")) for st in stations]
    prices_list = await asyncio.gather(*tasks)

    parsed_results = []
    for st, prices in zip(stations, prices_list):
        parsed_results.append({
            "Station ID": st.get("id"),
            "Station Name": st.get("name"),
            "Address": st.get("address", {}).get("line1"),
            "Location": {"Latitude": st.get("latitude"), "Longitude": st.get("longitude")},
            "Unit of Measure": prices.get("unit_of_measure"),
            "Currency": prices.get("currency"),
            "Image URL": prices.get("image_url"),
            "Regular Gas": prices.get("regular_gas"),
            "Premium Gas": prices.get("premium_gas"),
        })
    return parsed_results

# ------------------- SAVE TO EXCEL -------------------
def save_prices_to_excel(data: list[dict], filename: str = EXCEL_FILE):
    """Append gas station data to Excel, avoiding duplicates."""
    try:
        existing = pd.read_excel(filename)
    except FileNotFoundError:
        existing = pd.DataFrame(columns=[
            "Station ID", "Station Name", "Address", "Location", "Query Time",
            "Regular Last Update Time", "Regular Price", "Premium Last Update Time", "Premium Price"
        ])

    query_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_rows = []

    for st in data:
        regular, premium = st.get("Regular Gas", {}), st.get("Premium Gas", {})
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
        duplicate = existing[
            (existing["Station ID"] == new_row["Station ID"]) &
            (existing["Query Time"] == new_row["Query Time"])
        ]
        if duplicate.empty:
            new_rows.append(new_row)

    if new_rows:
        updated = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        updated.to_excel(filename, index=False)
        logging.info(f"Saved {len(new_rows)} new rows to {filename}")
    else:
        logging.info("No new data to save.")

# ------------------- MAIN -------------------
async def fetch_all_locations_and_zips():
    """Fetch and save prices for all locations and zip codes."""
    # Fetch by coordinates
    for lat, lon in LOCATIONS:
        logging.info(f"Fetching stations for ({lat},{lon})")
        response = await search_stations_by_coords(lat, lon)
        data = await parse_gas_stations(response)
        save_prices_to_excel(data)
        await asyncio.sleep(5)

    # Fetch by zip codes
    for zip_code in ZIP_CODES:
        logging.info(f"Fetching stations for zip code {zip_code}")
        response = await search_stations_by_zip(zip_code)
        data = await parse_gas_stations(response)
        save_prices_to_excel(data)
        await asyncio.sleep(5)

def main():
    try:
        asyncio.run(fetch_all_locations_and_zips())
    except Exception as e:
        logging.error(f"Error in main: {e}")

if __name__ == "__main__":
    # main()
    async def test(): 
        gb = GasBuddy()
        gb._load_cookies("data/cookies/my_cookies.json")
        result = await gb.location_search(lat=49.249, lon=-123.173)
        print(result)
    asyncio.run(test())
