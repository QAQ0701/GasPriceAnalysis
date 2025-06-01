import asyncio
import logging
import json
from gasbuddy import GasBuddy
import pandas as pd
from datetime import datetime
import time

# CONST
# default lat=49.249, lon=-123.173
locations = [(49.243, -123.0823), (49.173, -123.079), (49.15, -123.159)]  # lat,long

# Configure logging to view debug messages
logging.basicConfig(
    filename="./log/debug_log.txt",  # Specify the log file
    level=logging.DEBUG,  # Set the logging level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log message format
    filemode="w",  # 'w' for overwrite, 'a' for append
)


async def fetch_gas_prices(id):
    gasbuddy = GasBuddy(station_id=id)
    max_retries = 5
    backoff_factor = 1  # Initial backoff time in seconds

    for attempt in range(max_retries):
        try:
            response = await gasbuddy.price_lookup()
            logging.debug(f"Response: {response}")
            return response
        except Exception as e:
            # Check for specific error (e.g., rate-limiting)
            error_message = str(e).lower()
            if "too many requests" in error_message or "429" in error_message:
                wait_time = backoff_factor * (2**attempt)  # Exponential backoff
                logging.warning(f"Rate limit hit. Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logging.error(f"Failed to fetch prices for station {id}: {e}")
                return {"error": str(e)}
    logging.error(f"Max retries exceeded for station {id}.")
    return {"error": "Max retries exceeded"}


async def search_by_zipcode(zip_code):
    # Initialize the GasBuddy instance
    gasbuddy = GasBuddy()

    try:
        # Perform the location search using the postal code
        response = await gasbuddy.location_search(zipcode=zip_code)
        print("Search Results for Zip Code:", response)
        return response
    except Exception as e:
        print(f"Error during zip code search: {e}")


async def get_station_by_coor(lat, lon):
    print(lat, lon)
    gasbuddy = GasBuddy()
    response = await gasbuddy.location_search(lat, lon)
    if "error" in response:
        print("Error:", response["error"])
    else:
        print("Gas Stations", response)
        return response


# Parsing the response
async def parse_gas_stations(zip_code="V6M 3V2", lat=49.249, lon=-123.173):
    # response = await search_by_zipcode(zip_code)
    response = await get_station_by_coor(lat, lon)
    await asyncio.sleep(3)
    stations = (
        response.get("data", {})
        .get("locationBySearchTerm", {})
        .get("stations", {})
        .get("results", [])
    )

    tasks = []
    for station in stations:
        await asyncio.sleep(5)  # Add a delay between requests
        tasks.append(fetch_gas_prices(station.get("id")))
    prices = await asyncio.gather(*tasks)

    parsed_results = []
    logging.debug(f"stations: {stations}")
    for station, gas_prices in zip(stations, prices):
        # logging.debug("Appending gas prices")
        parsed_results.append(
            {
                "Station Name": station.get("name"),
                "Address": station.get("address", {}).get("line1"),
                "Station ID": station.get("id"),
                "Unit of Measure": gas_prices.get("unit_of_measure"),
                "Currency": gas_prices.get("currency"),
                "Location": {
                    "Latitude": gas_prices.get("latitude"),
                    "Longitude": gas_prices.get("longitude"),
                },
                "Image URL": gas_prices.get("image_url"),
                "Regular Gas": {
                    "Credit": gas_prices.get("regular_gas", {}).get("credit"),
                    "Price": gas_prices.get("regular_gas", {}).get("price"),
                    "Last Updated": gas_prices.get("regular_gas", {}).get(
                        "last_updated"
                    ),
                },
                "Premium Gas": {
                    "Credit": gas_prices.get("premium_gas", {}).get("credit"),
                    "Price": gas_prices.get("premium_gas", {}).get("price"),
                    "Last Updated": gas_prices.get("premium_gas", {}).get(
                        "last_updated"
                    ),
                },
            }
        )
    return parsed_results


def save_prices_to_excel(data: list[dict], filename: str = "./data/gas_prices.xlsx"):
    """
    Save gas station price data to an Excel file.

    Args:
        data (list[dict]): List of gas station data dictionaries.
        filename (str): Name of the Excel file to save to.
    """
    # Load existing data if the file exists
    try:
        existing_data = pd.read_excel(filename)
    except FileNotFoundError:
        existing_data = pd.DataFrame(
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

    new_rows = []
    query_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for station in data:
        try:
            station_id = station["Station ID"]
            station_name = station["Station Name"]
            address = station["Address"]
            location = station["Location"]
            regular = station["Regular Gas"]
            premium = station["Premium Gas"]
            location = station["Location"]
        except KeyError:
            logging.debug("Skipping station due to missing data")
            logging.debug(f"Missing data: {station}")
            continue

        # Create a new row for each station
        new_row = {
            "Station ID": station_id,
            "Station Name": station_name,
            "Address": address,
            "Location": location,
            "Query Time": query_time,
            "Regular Last Update Time": regular["Last Updated"],
            "Regular Price": regular["Price"],
            "Premium Last Update Time": premium["Last Updated"],
            "Premium Price": premium["Price"],
        }

        # Check if the exact station_id and query_time combination exists
        duplicate = existing_data[
            (existing_data["Station ID"] == station_id)
            & (existing_data["Query Time"] == query_time)
        ]
        if duplicate.empty:  # Only add if no duplicate exists
            new_rows.append(new_row)

    # Append new rows and save back to Excel
    if new_rows:
        updated_data = pd.concat(
            [existing_data, pd.DataFrame(new_rows)], ignore_index=True
        )
        updated_data.to_excel(filename, index=False)
        logging.debug(f"Data saved to {filename}")
    else:
        logging.debug("No new data to save.")


def main():
    try:
        # Searching using zip code
        parsed_data = asyncio.run(parse_gas_stations())
        save_prices_to_excel(parsed_data)
        time.sleep(60)
        parsed_data = asyncio.run(
            parse_gas_stations(lat=locations[0][0], lon=locations[0][1])
        )  # (49.243, -123.0823))
        save_prices_to_excel(parsed_data)
        time.sleep(60)
        parsed_data = asyncio.run(
            parse_gas_stations(lat=locations[1][0], lon=locations[1][1])
        )  # (49.173, -123.079))
        save_prices_to_excel(parsed_data)
        time.sleep(60)
        parsed_data = asyncio.run(
            parse_gas_stations(lat=locations[2][0], lon=locations[2][1])
        )  # (49.15, lon=-123.159))
        save_prices_to_excel(parsed_data)

        # V6M 3V2
        # V6M 2V6
        # V6P 2Z2
        # V6X 3Z9
    except Exception as e:
        print(f"An error occurred: {e}")

    # # Print the results
    # for station in parsed_data:
    #     try:
    #         print(f"Station Name: {station['Station Name']}")
    #         print(f"Address: {station['Address']}")
    #         print(f"Station ID: {station['Station ID']}\n")
    #         print(f"Unit of Measure: {station['Unit of Measure']}")
    #         print(f"Currency: {station['Currency']}")
    #         print(f"Location: {station['Location']}")
    #         print(f"Image URL: {station['Image URL']}")
    #         print(f"Regular Gas: {station['Regular Gas']}")
    #         print(f"Premium Gas: {station['Premium Gas']}\n")
    #     except KeyError:
    #         print("\nKeyError:")
    #         print(station)
    #         print(type(station))


# Run the script
main()
