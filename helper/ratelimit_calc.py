import asyncio
import aiohttp
import json
import time
import csv
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

LOCATION_QUERY_PRICES = "query LocationBySearchTerm($brandId: Int, $cursor: String, $fuel: Int, $lat: Float, $lng: Float, $maxAge: Int, $search: String) { locationBySearchTerm(lat: $lat, lng: $lng, search: $search) { stations(brandId: $brandId cursor: $cursor fuel: $fuel lat: $lat lng: $lng maxAge: $maxAge) { results { address { line1 } prices { cash { nickname postedTime price } credit { nickname postedTime price } fuelProduct longName } priceUnit currency id latitude longitude } } trends { areaName country today todayLow trend } } }"

# --- Helper to load cookies ---
COOKIE_FILE = "data/cookies/my_cookies.json"  # <- your cookie dump file
LOG_FILE = "log/rate_limit_log.csv"


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

print(HEADERS)
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


# --- CSV setup ---
def init_csv():
    with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "request_index",
                "delay_sec",
                "status",
                "http_code",
                "message_snippet",
                "success_count_before_block",
            ]
        )


def log_csv(idx, delay, status, http_code, msg, success_count):
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        ts = datetime.utcnow().isoformat()
        snippet = (msg or "")[:100].replace("\n", " ")
        writer.writerow(
            [ts, idx, f"{delay:.2f}", status, http_code, snippet, success_count]
        )


# --- Request function ---
async def send_request(session, idx, delay, success_count):
    try:
        async with session.post(GRAPHQL_URL, data=json.dumps(TEST_QUERY)) as resp:
            text = await resp.text()
            if resp.status == 200:
                print(f"[{idx}] OK")
                log_csv(idx, delay, "OK", 200, text, success_count)
                # # Parse JSON and print the 'data' field
                # try:
                #     response_json = json.loads(text)
                #     data = response_json.get("data")
                #     print(f"[{idx}] Response data:", json.dumps(data, indent=2))
                # except json.JSONDecodeError:
                #     print(f"[{idx}] Failed to parse JSON")
                return True
            else:
                print(f"[{idx}] BLOCKED {resp.status} {text[:80]}")
                log_csv(idx, delay, "BLOCKED", resp.status, text, success_count)
                return False
    except Exception as e:
        print(f"[{idx}] ERROR: {e}")
        log_csv(idx, delay, "ERROR", "NA", str(e), success_count)
        return False


# --- Main rate test ---
async def main():
    init_csv()
    
    async with aiohttp.ClientSession(headers=HEADERS, cookies=COOKIES) as session:
        delay = 5.0  # start slow
        idx = 0
        success_count = 0
        idx += 1
    #     await send_request(session, idx, delay, success_count)
        while True:
            idx += 1
            ok = await send_request(session, idx, delay, success_count)
            if ok:
                success_count += 1
            else:
                print("\n*** BLOCK DETECTED ***")
                block_time = time.time()
                print("Waiting to see when block clears...")
                while True:
                    await asyncio.sleep(30)
                    if await send_request(session, f"retry-{idx}", 30, success_count):
                        unblock_time = time.time()
                        block_duration = unblock_time - block_time
                        print(f"Block duration: {block_duration:.1f} seconds")
                        log_csv(
                            idx,
                            30,
                            "UNBLOCKED",
                            200,
                            f"Block duration {block_duration:.1f}s",
                            success_count,
                        )
                        return
                break

            if idx % 10 == 0 and delay > 0.2:
                delay *= 0.5
                print(f"\nSpeeding up → delay now {delay:.2f}s/request\n")
            await asyncio.sleep(delay)

def plot_delay_over_time():
    # Read CSV file
    df = pd.read_csv("log/rate_limit_log.csv", parse_dates=["timestamp"])

    # Plot delay over time, color-coded by status
    plt.figure(figsize=(12,6))

    # Map status to colors
    status_colors = {
        "OK": "green",
        "BLOCKED": "red",
        "UNBLOCKED": "blue",
        "retry-22": "orange"
    }

    # Scatter plot
    for status, color in status_colors.items():
        subset = df[df["status"] == status]
        plt.scatter(subset["timestamp"], subset["delay_sec"], 
                    label=status, color=color, s=50)

    plt.xlabel("Timestamp")
    plt.ylabel("Delay (sec)")
    plt.title("Request Delay Over Time")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # asyncio.run(main())
    plot_delay_over_time()
