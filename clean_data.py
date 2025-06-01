import pandas as pd
import logging
import os

# Configure logging to view debug messages
logging.basicConfig(
    filename="./log/debug_log.txt",  # Specify the log file
    level=logging.DEBUG,  # Set the logging level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log message format
    filemode="a",  # 'w' for overwrite, 'a' for append
)

# Load the Excel file
file_path = "./data/gas_prices.xlsx"  # Change if needed
output_path = "./data/cleaned_gas_prices.xlsx"
df = pd.read_excel(file_path)

# Convert 'Query Time' to datetime FIRST
df["Query Time"] = pd.to_datetime(df["Query Time"], errors="coerce")

# Drop rows where 'Query Time' couldn't be parsed
df = df.dropna(subset=["Query Time"])

# Remove rows with both Regular and Premium prices missing
df = df.dropna(subset=["Regular Price", "Premium Price"], how="all")


# Add 'Time Tag' column based on the hour of 'Query Time'
def tag_time(hour):
    if 8 <= hour < 10:
        return "morning"
    elif 13 <= hour < 16:
        return "afternoon"
    elif 22 <= hour < 24:
        return "evening"
    elif 2 <= hour < 4:
        return "midnight"
    else:
        return "other"


df["Time Tag"] = df["Query Time"].dt.hour.apply(tag_time)

# Extract the date part for deduplication
df["Query Date"] = df["Query Time"].dt.normalize()

# Drop duplicates based on Station ID, Time Tag, and Query Date
df = df.drop_duplicates(subset=["Station ID", "Time Tag", "Query Date"])

# Sort by Station ID
df = df.sort_values(by="Station ID")

try:
    if os.path.exists(output_path):
        logging.debug(f"File {output_path} already exists. Deleting it.")
        os.remove(output_path)
    # Save to Excel
    df.to_excel(output_path, index=False)
except Exception as e:
    logging.debug(f"An error occurred: {e}")

# Preview
logging.debug(df[["Station ID", "Query Time", "Time Tag"]].head())
