import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import folium
import branca.colormap as cm
import logging
import os
from plotly.offline import plot
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import ast
from datetime import date

hm_avg_output_path = "./output/heatmap.html"
hm_today_output_path = "./output/heatmap_today.html"
ts_output_path = "./output/time_series.png"
it_output_path = "./output/interactive_graph.html"
bar_output_path = "./output/bar_chart.png"

# Configure logging
logging.basicConfig(
    filename="./log/debug_log.txt",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)

logging.debug("\nVisualizing gas prices data...")

# Load cleaned data
df = pd.read_excel("./data/cleaned_gas_prices.xlsx")

# Treat 0 prices as missing
for col in ["Regular Price", "Premium Price"]:
    zero_count = (df[col] == 0).sum()
    if zero_count > 0:
        logging.debug(f"{zero_count} zero values found in '{col}', converting to NaN.")
        df.loc[df[col] == 0, col] = pd.NA


# ---------------- Time Series Plot ----------------
def plotTimeGraph(df):
    df_ts = df.copy()
    df_ts["Query Time"] = pd.to_datetime(df_ts["Query Time"], errors="coerce")
    df_ts = df_ts.dropna(subset=["Query Time"])  # only drop rows with invalid times
    df_ts["RegularDate"] = df_ts["Regular Last Update Time"].dt.date
    df_ts["PremiumDate"] = df_ts["Premium Last Update Time"].dt.date
    df_ts["rTime Tag"] = df_ts["rTime Tag"].str.lower().str.strip()
    df_ts["pTime Tag"] = df_ts["pTime Tag"].str.lower().str.strip()

    pivot_regular = df_ts.pivot_table(
        index="RegularDate", columns="rTime Tag", values="Regular Price", aggfunc="mean"
    )
    pivot_premium = df_ts.pivot_table(
        index="PremiumDate", columns="pTime Tag", values="Premium Price", aggfunc="mean"
    )

    plt.figure(figsize=(12, 6))
    for tag in df_ts["rTime Tag"].unique():
        if tag in pivot_regular.columns:
            plt.plot(
                pivot_regular.index,
                pivot_regular[tag],
                label=f"Regular {tag}",
                marker="o",
            )
    for tag in df_ts["pTime Tag"].unique():
        if tag in pivot_premium.columns:
            plt.plot(
                pivot_premium.index,
                pivot_premium[tag],
                linestyle="--",
                label=f"Premium {tag}",
                marker="x",
            )

    plt.xlabel("Date")
    plt.ylabel("Price (cents/liter)")
    plt.title("Gas Price Trends by Time of Day")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    try:
        if os.path.exists(ts_output_path):
            logging.debug(f"File {ts_output_path} already exists. Deleting it.")
            os.remove(ts_output_path)
        plt.savefig(ts_output_path, format="png", dpi=300)
        plt.close()
        logging.debug(f"Time graph saved to '{ts_output_path}'.")
    except Exception as e:
        logging.debug(f"An error occurred: {e}")


# ---------------- Heatmap ----------------
def plotHeatMap(prices, path):
    # Initialize the map
    map_center = [prices["Latitude"].mean(), prices["Longitude"].mean()]
    map_gas_prices = folium.Map(location=map_center, zoom_start=12)

    # Regular layer
    regular_color_scale = cm.LinearColormap(
        colors=["green", "yellow", "red"],
        vmin=prices["Regular Price"].min(),
        vmax=prices["Regular Price"].max(),
        caption="Regular Gas Prices",
    )
    regular_layer = folium.FeatureGroup(name="Regular Gas Prices", show=True)
    for _, row in prices.iterrows():
        if pd.notna(row["Regular Price"]):
            color = regular_color_scale(row["Regular Price"])
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=7,
                popup=f"Station: {row['Station Name']}<br>Regular Price: {row['Regular Price']:.2f}",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
            ).add_to(regular_layer)
    map_gas_prices.add_child(regular_layer)
    regular_color_scale.add_to(map_gas_prices)

    # Premium layer
    premium_color_scale = cm.LinearColormap(
        colors=["blue", "purple", "pink"],
        vmin=prices["Premium Price"].min(),
        vmax=prices["Premium Price"].max(),
        caption="Premium Gas Prices",
    )
    premium_layer = folium.FeatureGroup(name="Premium Gas Prices", show=False)
    for _, row in prices.iterrows():
        if pd.notna(row["Premium Price"]):
            color = premium_color_scale(row["Premium Price"])
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=7,
                popup=f"Station: {row['Station Name']}<br>Premium Price: {row['Premium Price']:.2f}",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
            ).add_to(premium_layer)
    map_gas_prices.add_child(premium_layer)
    premium_color_scale.add_to(map_gas_prices)

    folium.LayerControl().add_to(map_gas_prices)

    try:
        if os.path.exists(path):
            logging.debug(f"File {path} already exists. Deleting it.")
            os.remove(path)
        map_gas_prices.save(path)
        logging.debug(f"Interactive map saved to '{path}'.")
    except Exception as e:
        logging.debug(f"An error occurred: {e}")


def generate_heatmap_data(df):
    df_hm = df.copy()
    # Safely parse Latitude/Longitude
    df_hm["Latitude"] = df_hm["Location"].apply(
        lambda x: ast.literal_eval(x).get("Latitude")
    )
    df_hm["Longitude"] = df_hm["Location"].apply(
        lambda x: ast.literal_eval(x).get("Longitude")
    )
    df_hm["Query Date"] = df_hm["Query Date"].dt.date
    today = date.today()

    # Drop rows with missing coordinates
    df_hm = df_hm.dropna(subset=["Latitude", "Longitude"])

    # Clip prices
    df_hm["Regular Price"] = df_hm["Regular Price"].clip(lower=100, upper=300)
    df_hm["Premium Price"] = df_hm["Premium Price"].clip(lower=100, upper=400)

    avg_prices = df_hm.groupby(
        ["Station ID", "Station Name", "Latitude", "Longitude"], as_index=False
    ).agg({"Regular Price": "mean", "Premium Price": "mean"})

    # # Drop rows where all prices are missing
    # avg_prices = avg_prices.dropna(subset=["Regular Price", "Premium Price"], how="all")
    # if avg_prices.empty:
    #     logging.debug("No valid stations to plot heatmap.")
    #     return

    plotHeatMap(avg_prices, hm_avg_output_path)

    # Filter by today's dat
    df_hm = df_hm[df_hm["Query Date"] == today]
    # For each row, take the max of the two timestamps
    df_hm["Latest Update Time"] = df_hm[
        ["Regular Last Update Time", "Premium Last Update Time"]
    ].max(axis=1)

    # Get index of the row with the most recent update per Station ID
    idx = df_hm.groupby("Station ID")["Latest Update Time"].idxmax()
    idx = idx.dropna().astype(int)

    # Keep only those rows
    df_hm = df_hm.loc[idx].reset_index(drop=True)

    # output_path = "./data/today.xlsx"
    # print(f"Today's Heatmap: {df_hm}")
    # try:
    #     if os.path.exists(output_path):
    #         logging.debug(f"File {output_path} already exists. Deleting it.")
    #         os.remove(output_path)
    #     df_hm.to_excel(output_path, index=False)
    # except Exception as e:
    #     logging.debug(f"An error occurred: {e}")

    today_prices = df_hm.groupby(
        ["Station ID", "Station Name", "Latitude", "Longitude"], as_index=False
    ).agg({"Regular Price": "mean", "Premium Price": "mean"})

    plotHeatMap(today_prices, hm_today_output_path)


# ---------------- Interactive Plot ----------------
def plotInteractive(df):
    df_it = df.copy()
    df_it["Query Time"] = pd.to_datetime(df_it["Query Time"], errors="coerce")
    df_it = df_it.dropna(subset=["Query Time"])  # only drop invalid times
    df_it["Date"] = df_it["Query Time"].dt.date
    df_it["rTime Tag"] = df_it["rTime Tag"].str.lower().str.strip()
    df_it["pTime Tag"] = df_it["pTime Tag"].str.lower().str.strip()
    # df_it["mTime Tag"] = df_it["Time Tag"].str.lower().str.strip()
    # df_it["dTime Tag"] = df_it["Time Tag"].str.lower().str.strip()

    time_colors = {
        "morning": "orange",
        "afternoon": "green",
        "evening": "blue",
        "midnight": "purple",
    }
    fig = make_subplots(
        rows=2, cols=1, subplot_titles=("Regular Gas Prices", "Premium Gas Prices")
    )

    for tag in df_it["rTime Tag"].unique():
        sub_df = df_it[df_it["rTime Tag"] == tag]

        # Regular prices
        sub_df_regular = sub_df[sub_df["Regular Price"].notna()]
        fig.add_trace(
            go.Scatter(
                x=sub_df_regular["Query Time"],
                y=sub_df_regular["Regular Price"],
                mode="markers",
                name=f"Regular - {tag}",
                marker=dict(color=time_colors.get(tag, "gray"), size=9),
                hovertext=sub_df_regular.apply(
                    lambda row: f"Station: {row['Station Name']}<br>ID: {row['Station ID']}<br>Add: {row['Address']}",
                    axis=1,
                ),
                hoverinfo="text+x+y",
            ),
            row=1,
            col=1,
        )

    for tag in df_it["pTime Tag"].unique():
        sub_df = df_it[df_it["pTime Tag"] == tag]
        # Premium prices
        sub_df_premium = sub_df[sub_df["Premium Price"].notna()]
        fig.add_trace(
            go.Scatter(
                x=sub_df_premium["Query Time"],
                y=sub_df_premium["Premium Price"],
                mode="markers",
                name=f"Premium - {tag}",
                marker=dict(
                    color=time_colors.get(tag, "gray"), size=9, symbol="diamond"
                ),
                hovertext=sub_df_premium.apply(
                    lambda row: f"Station: {row['Station Name']}<br>ID: {row['Station ID']}<br>Add: {row['Address']}",
                    axis=1,
                ),
                hoverinfo="text+x+y",
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        height=1600,
        title_text="Gas Prices by Time of Day and Type (Interactive)",
        template="plotly_white",
        legend_title_text="Fuel Type & Time Tag",
        xaxis_title="Date",
        yaxis_title="Price (cents/liter)",
        xaxis2_title="Date",
        yaxis2_title="Price (cents/liter)",
    )

    try:
        if os.path.exists(it_output_path):
            logging.debug(f"File {it_output_path} already exists. Deleting it.")
            os.remove(it_output_path)
        plot(fig, filename=it_output_path, auto_open=False)
        logging.debug(f"Interactive graph saved to '{it_output_path}'.")
    except Exception as e:
        logging.debug(f"An error occurred: {e}")


def plotBarChart(df):
    tickHeight = 10
    # Ensure Query Date is datetime
    df["Query Date"] = pd.to_datetime(df["Query Date"])

    # Get weekday names
    df["Weekday"] = df["Query Date"].dt.day_name()

    # Group by weekday and take average prices
    avg_prices = df.groupby("Weekday", as_index=False).agg(
        {"Regular Price": "mean", "Premium Price": "mean"}
    )

    # Order weekdays Monday → Sunday
    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    avg_prices["Weekday"] = pd.Categorical(
        avg_prices["Weekday"], categories=weekday_order, ordered=True
    )
    avg_prices = avg_prices.sort_values("Weekday")

    # Plot grouped bar chart
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    plt.grid(True, zorder=1)
    bar_width = 0.1
    x = range(len(avg_prices))

    # Determine y-axis max for shading
    y_max = max(avg_prices[["Regular Price", "Premium Price"]].max()) + 10

    # Add alternating horizontal bands
    band_height = tickHeight  # match your yticks increment
    for y in range(0, int(y_max), band_height * 2):
        ax.axhspan(y, y + band_height, facecolor="gray", alpha=0.2, zorder=0)
    plt.bar(
        [i - bar_width / 2 for i in x],
        avg_prices["Regular Price"],
        width=bar_width,
        label="Regular",
        alpha=0.8,
    )
    plt.bar(
        [i + bar_width / 2 for i in x],
        avg_prices["Premium Price"],
        width=bar_width,
        label="Premium",
        alpha=0.8,
    )

    plt.xticks(x, avg_prices["Weekday"], rotation=30)
    plt.xlabel("Day of Week")
    plt.ylabel("Price (¢/L)")
    plt.title("Average Regular vs Premium Gas Price by Day of Week")
    plt.yticks(range(0, int(y_max), tickHeight))  # ticks every 10¢
    plt.yticks(fontsize=9)
    plt.legend()

    plt.tight_layout()

    try:
        if os.path.exists(bar_output_path):
            logging.debug(f"File {bar_output_path} already exists. Deleting it.")
            os.remove(bar_output_path)
        plt.savefig(bar_output_path, format="png", dpi=300)
        plt.close()
        logging.debug(f"Time graph saved to '{bar_output_path}'.")
    except Exception as e:
        logging.debug(f"An error occurred: {e}")


# ---------------- Run All Plots ----------------
plotTimeGraph(df)
plotInteractive(df)
plotBarChart(df)
generate_heatmap_data(df)

logging.info("All plots completed.")
