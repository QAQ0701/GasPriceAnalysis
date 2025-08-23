import pandas as pd
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Your ISO check function
def is_iso_string(s: str) -> bool:
    ISO_UTC_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
    if not isinstance(s, str):
        return False
    return bool(ISO_UTC_REGEX.match(s))

# Your UTC → PDT conversion function
def iso_to_pdt(utc_time: str):
    """Convert UTC ISO string to PDT naive datetime for Excel."""
    try:
        dt_utc = pd.to_datetime(utc_time, utc=True)
        dt_pdt = dt_utc.tz_convert("America/Los_Angeles")
        dt_excel = dt_pdt.tz_localize(None)
        return dt_excel
    except Exception as e:
        logging.error(f"Error converting time '{utc_time}': {e}")
        return None

# Columns to check
TIME_COLUMNS = [
    "Regular Last Update Time",
    "Premium Last Update Time",
]

def convert_excel_times(filename: str, output_file: str = None):
    """Read Excel, convert ISO times to PDT, and optionally save back."""
    df = pd.read_excel(filename)
    logging.info(f"Loaded {len(df)} rows from {filename}")

    for col in TIME_COLUMNS:
        if col not in df.columns:
            logging.warning(f"Column '{col}' not found in Excel, skipping.")
            continue

        # Apply conversion
        def convert_cell(cell):
            if is_iso_string(cell):
                return iso_to_pdt(cell)
            return cell  # leave as-is if not ISO

        df[col] = df[col].apply(convert_cell)

    logging.info("Finished converting ISO times to PDT.")

    # Save back if output_file is provided
    if output_file:
        df.to_excel(output_file, index=False)
        logging.info(f"Saved updated Excel to {output_file}")

    return df

# Example usage
df_updated = convert_excel_times("data/gas_prices copy.xlsx", "data/gas_prices_pdt.xlsx")
