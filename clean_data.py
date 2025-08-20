import pandas as pd
import logging
import os

# Configure logging
logging.basicConfig(
    filename="./log/debug_log.txt",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)
logging.debug("\nCleaning gas prices data...")

# Load the Excel file
file_path = "./data/gas_prices.xlsx"
output_path = "./data/cleaned_gas_prices.xlsx"
df = pd.read_excel(file_path)

# Convert 'Query Time' to datetime first
df["Query Time"] = pd.to_datetime(df["Query Time"], errors="coerce")
# df["Query Time"] = df["Query Time"] - pd.Timedelta(hours=15)  # Adjust timezone

# Drop rows where 'Query Time' couldn't be parsed
df = df.dropna(subset=["Query Time"])

# Remove rows with both Regular and Premium prices missing
df = df.dropna(subset=["Regular Price", "Premium Price"], how="all")

# # --- Fill missing update times ---
# for col in ["Regular Last Update Time", "Premium Last Update Time"]:
#     missing_count = df[col].isna().sum()
#     if missing_count > 0:
#         logging.debug(f"{missing_count} missing values found in '{col}', filling with 'Query Time'.")
#         df[col] = df[col].fillna(df["Query Time"])

# Add 'Time Tag' column based on the hour of 'Query Time'
def tag_time(hour):
    if 7 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour <= 24:
        return "evening"
    elif 1 <= hour < 7:
        return "midnight"
    else:
        return "midnight"

df["Time Tag"] = df["Query Time"].dt.hour.apply(tag_time)

# # Extract the date part for deduplication
# df["Query Date"] = df["Query Time"].dt.normalize()

# # Drop duplicates based on Station ID, Time Tag, and Query Date
# df = df.drop_duplicates(subset=["Station ID", "Time Tag", "Query Date"])

# Sort by Station ID
df = df.sort_values(by="Station ID")

# Save to Excel
try:
    if os.path.exists(output_path):
        logging.debug(f"File {output_path} already exists. Deleting it.")
        os.remove(output_path)
    df.to_excel(output_path, index=False)
except Exception as e:
    logging.debug(f"An error occurred: {e}")

# Preview
logging.debug(df[["Station ID", "Query Time", "Regular Last Update Time", "Premium Last Update Time", "Time Tag"]].head())
