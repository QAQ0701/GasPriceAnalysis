import pandas as pd
import numpy as np
import logging
import os
import re


# Configure logging
logging.basicConfig(
    filename="./log/debug_log.txt",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)
logging.debug("\nCleaning gas prices data...")
# --------HELPER--------

# --------------Load the Excel file ---------------
file_path = "./data/gas_prices.xlsx"
output_path = "./data/cleaned_gas_prices.xlsx"
df = pd.read_excel(file_path)

# -------- Data Cleaning --------
# Convert 'Query Time' to datetime first
df["Query Time"] = pd.to_datetime(df["Query Time"], errors="coerce")
# df["Query Time"] = df["Query Time"] - pd.Timedelta(hours=15)  # Adjust timezone

# Convert last update times
# df["Regular Last Update Time"] = pd.to_datetime(df["Regular Last Update Time"], errors="coerce")
# df["Premium Last Update Time"] = pd.to_datetime(df["Premium Last Update Time"], errors="coerce")
# df["Midgrade Last Update Time"] = pd.to_datetime(df["Midgrade Last Update Time"], errors="coerce")
# df["Diesel Last Update Time"] = pd.to_datetime(df["Diesel Last Update Time"], errors="coerce")

# Drop rows where 'Query Time' couldn't be parsed
df = df.dropna(subset=["Query Time"])

# # --- Fill missing update times ---
# for col in ["Regular Last Update Time", "Premium Last Update Time"]:
#     missing_count = df[col].isna().sum()
#     if missing_count > 0:
#         logging.debug(f"{missing_count} missing values found in '{col}', filling with 'Query Time'.")
#         df[col] = df[col].fillna(df["Query Time"])


# Add 'qTime Tag' column based on the hour of 'Query Time'
def tag_time(hour):
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour <= 24:
        return "evening"
    elif 1 <= hour < 6:
        return "midnight"
    else:
        return "midnight"


df["qTime Tag"] = df["Query Time"].dt.hour.apply(tag_time)
df["rTime Tag"] = df["Regular Last Update Time"].dt.hour.apply(tag_time)
df["pTime Tag"] = df["Premium Last Update Time"].dt.hour.apply(tag_time)
df["mTime Tag"] = df["Midgrade Last Update Time"].dt.hour.apply(tag_time)
df["dTime Tag"] = df["Diesel Last Update Time"].dt.hour.apply(tag_time)
# Extract the date part for deduplication
df["Query Date"] = df["Query Time"].dt.normalize()

# ------------ Remove duplicate rows --------------

# Find duplicates (excluding the first occurrence)
dupes = df.duplicated(
    subset=["Station ID", "Regular Last Update Time", "Regular Price"], keep="first"
)

# Set both columns to NaN only in duplicate rows
df.loc[dupes, ["Regular Last Update Time", "Regular Price"]] = np.nan

# Sort by Station ID
df = df.sort_values(by="Station ID")

# Remove rows with all prices missing
df = df.dropna(
    subset=["Regular Price", "Premium Price", "Midgrade Price", "Diesel Price"],
    how="all",
)

# ---------Save to Excel----------
try:
    if os.path.exists(output_path):
        logging.debug(f"File {output_path} already exists. Deleting it.")
        os.remove(output_path)
    df.to_excel(output_path, index=False)
except Exception as e:
    logging.debug(f"An error occurred: {e}")

# Preview
logging.debug(
    df[
        [
            "Station ID",
            "Query Time",
            "Regular Last Update Time",
            "Premium Last Update Time",
            "qTime Tag",
        ]
    ].head()
)
