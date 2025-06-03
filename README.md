# Codebase Documentation: Gas Price Analysis Pipeline

## Introduction

This document provides an overview of the gas price data pipeline consisting of three Python scripts:

- `scrape_gasprice.py`
- `clean_data.py`
- `visualization.py`
- https://htmlpreview.github.io/?https://github.com/QAQ0701/GasPriceAnalysis/blob/main/visualization.html

---

## Overview of the Pipeline

The pipeline is executed in three sequential steps:

1. **`scrape_gasprice.py`**: Collects raw gas price data for specified geographic locations using the GasBuddy API and saves it to an Excel file.
2. **`clean_data.py`**: Reads the raw data, performs cleaning operations such as timestamp conversion, deduplication, and tagging, and outputs a cleaned dataset.
3. **`visualization.py`**: Loads the cleaned data and generates two visual outputs—a time-series plot of average gas prices by time of day, an interactive geographic heatmap of station prices, and a scatter plot of all the data points. These outputs are saved as image files and an HTML file for map interaction.

---

## `scrape_gasprice.py`

### Purpose:

- Connects to the GasBuddy API to retrieve gas station information and current prices for multiple locations (latitude and longitude coordinates).

### Key Functionalities:

- **Configuration**: Specifies a list of geographic coordinates for targeted searches.
- **Asynchronous Requests**: Uses `asyncio` to perform API calls concurrently, retrieving station lists and detailed price data.
- **Data Parsing**: Extracts fields such as station name, address, ID, pricing details (regular and premium), units, and timestamps.
- **Data Storage**: Consolidates the parsed data into a tabular structure and appends new entries to a master Excel file (`gas_prices.xlsx`).
- **Logging**: Records debug information and errors to a log file to help diagnose issues.
- **Execution Flow**: Calls `parse_gas_stations()` for each predefined location with a 60-second pause between runs to respect API rate limits.

### Output:

- `./data/gas_prices.xlsx`: Contains cumulative gas price records with timestamps, appendable across script executions.

---

## `clean_data.py`

### Purpose:

- Loads the raw gas price data from `gas_prices.xlsx` and prepares it for analysis by cleaning, filtering, and deduplicating records.

### Key Functionalities:

- **Data Loading**: Reads the Excel file into a `pandas` DataFrame.
- **Timestamp Conversion**: Converts the "Query Time" column to datetime objects and drops invalid rows.
- **Filtering**: Removes records with missing regular and premium prices.
- **Time Tagging**: Adds a "Time Tag" column (e.g., morning, afternoon, evening) based on the query hour.
- **Date Extraction**: Derives "Query Date" for deduplication.
- **Deduplication**: Ensures one record per station per time bucket per day.
- **Sorting & Output**: Sorts by Station ID and writes cleaned results to a new file (`cleaned_gas_prices.xlsx`).

### Output:

- `./data/cleaned_gas_prices.xlsx`: Ready for visualization and analysis.

---

## `visualization.py`

### Purpose:

- Generates visual insights from the cleaned gas price data, showing time-based trends and geographic distribution.

### Key Functionalities:

- **Data Loading**: Reads data from `cleaned_gas_prices.xlsx`.
- **Time-Series Plot (`plotTimeGraph`)**:
  - Creates a line chart showing average regular and premium gas prices by time of day (Time Tag).
  - Saves chart to `./output/time_plot.png`.
- **Geographic Heatmap (`plotHeatMap`)**:
  - Parses latitude/longitude from location data.
  - Clips extreme price values to manage outliers.
  - Computes average prices per station.
  - Creates an interactive map using Folium with price-coded markers.
  - Outputs `./output/heatmap.html`.
- **Scatter Plote (`plotHeatMap`)**:
  -plots all data points on a time and price scale.

### Outputs:

- `./output/time_plot.png`
- `./output/heatmap.html`
- `./output/interactive_graph.html`

---

## Dependencies

Ensure the following Python packages are installed:

- `asyncio` – asynchronous operations
- `logging` – logging runtime activity
- `pandas` – data manipulation and Excel I/O
- `datetime`, `time` – standard time handling
- `gasbuddy` – (3rd party) API access
- `matplotlib` – plotting
- `folium`, `branca`, `plotly`

Use `pip install <package>` as needed.

---

## Running the Pipeline

1. Run `scrape_gasprice.py` to collect raw gas price data (execution may take several minutes).
2. Run `clean_data.py` to clean and deduplicate the data.
3. Run `visualization.py` to generate the visual outputs.

Alternatively, you can automate the process using the `autorun.sh` script in a timed loop.

**Time slots** are:

- `08:00` – morning
- `14:00` – afternoon
- `20:00` – evening
- `02:00` – midnight  
  _(Each time window allows a +1 hour range due to system shortcut limitations on macOS.)_

---

## Notes:

- Logs are saved to `./log/debug_log.txt`. Use this to troubleshoot errors or verify execution steps.
- `gas_prices.xlsx` accumulates records across runs. Consider archiving or rotating it to manage size.
- "Time Tag" categories are: `morning`, `afternoon`, `evening`, `midnight`, and `other`. Ensure these match reporting needs.
- The heatmap clips prices to avoid visual distortion. You can adjust thresholds in `visualization.py` if needed.
- Scrape script includes API delay buffers; further throttling may be required for high-frequency automation.
