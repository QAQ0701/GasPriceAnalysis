import pandas as pd
import matplotlib.pyplot as plt
import folium
# from folium.plugins import HeatMap
import branca.colormap as cm

# Load cleaned data
df = pd.read_excel("./data/cleaned_gas_prices.xlsx")

def plotTimeGraph(df):
    # Prepare date and time tags
    df['Query Time'] = pd.to_datetime(df['Query Time'], errors='coerce')
    df = df.dropna(subset=['Query Time'])
    df['Date'] = df['Query Time'].dt.date
    df['Time Tag'] = df['Time Tag'].str.lower().str.strip()

    # Pivot
    pivot_regular = df.pivot_table(index='Date', columns='Time Tag', values='Regular Price', aggfunc='mean')
    pivot_premium = df.pivot_table(index='Date', columns='Time Tag', values='Premium Price', aggfunc='mean')

    # Plot
    plt.figure(figsize=(12, 6))

    for tag in df['Time Tag'].unique():
        if tag in pivot_regular.columns:
            plt.plot(pivot_regular.index, pivot_regular[tag], label=f'Regular {tag}', marker='o')
        if tag in pivot_premium.columns:
            plt.plot(pivot_premium.index, pivot_premium[tag], linestyle='--', label=f'Premium {tag}', marker='x')

    plt.xlabel('Date')
    plt.ylabel('Price (cents/liter)')
    plt.title('Gas Price Trends by Time of Day')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()    
def plotHeatMap(df):
    # Extract latitude and longitude from the 'Location' column
    df['Latitude'] = df['Location'].apply(lambda x: eval(x)['Latitude'])
    df['Longitude'] = df['Location'].apply(lambda x: eval(x)['Longitude'])

    # Handle missing data: Drop rows with missing prices
    df = df.dropna(subset=['Regular Price', 'Premium Price'])

    # Handle missing data: Ensure reasonable price ranges by clipping extreme values
    df['Regular Price'] = df['Regular Price'].clip(lower=100, upper=200)
    df['Premium Price'] = df['Premium Price'].clip(lower=150, upper=250)

    # Group by Station ID to calculate the average price for each station
    avg_prices = df.groupby(['Station ID', 'Station Name', 'Latitude', 'Longitude'], as_index=False).agg({
        'Regular Price': 'mean',
        'Premium Price': 'mean'
    })

    # Verify and adjust thresholds for regular prices
    min_regular = avg_prices['Regular Price'].min()
    max_regular = avg_prices['Regular Price'].max()
    if min_regular < max_regular:
        regular_color_scale = cm.LinearColormap(
            colors=['green', 'yellow', 'red'],
            vmin=min_regular,
            vmax=max_regular,
            caption="Regular Gas Prices"
        )
    else:
        print(f"Warning: Invalid thresholds for regular prices. min_regular={min_regular}, max_regular={max_regular}")

    # Verify and adjust thresholds for premium prices
    min_premium = avg_prices['Premium Price'].min()
    max_premium = avg_prices['Premium Price'].max()
    if min_premium < max_premium:
        premium_color_scale = cm.LinearColormap(
            colors=['blue', 'purple', 'pink'],
            vmin=min_premium,
            vmax=max_premium,
            caption="Premium Gas Prices"
        )
    else:
        print(f"Warning: Invalid thresholds for premium prices. min_premium={min_premium}, max_premium={max_premium}")

    # Initialize the map centered at the average latitude and longitude
    map_center = [avg_prices['Latitude'].mean(), avg_prices['Longitude'].mean()]
    map_gas_prices = folium.Map(location=map_center, zoom_start=12)

    # Create a feature group for regular prices
    regular_layer = folium.FeatureGroup(name="Regular Gas Prices")
    if min_regular < max_regular:  # Only add the layer if valid thresholds exist
        for _, row in avg_prices.iterrows():
            color = regular_color_scale(row['Regular Price'])
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=7,
                popup=(
                    f"Station: {row['Station Name']}<br>"
                    f"Regular Price: {row['Regular Price']:.2f}"
                ),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
            ).add_to(regular_layer)
        map_gas_prices.add_child(regular_layer)
        # Add the legend for regular prices
        regular_color_scale.add_to(map_gas_prices)

    # Create a feature group for premium prices
    premium_layer = folium.FeatureGroup(name="Premium Gas Prices")
    if min_premium < max_premium:  # Only add the layer if valid thresholds exist
        for _, row in avg_prices.iterrows():
            color = premium_color_scale(row['Premium Price'])
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=7,
                popup=(
                    f"Station: {row['Station Name']}<br>"
                    f"Premium Price: {row['Premium Price']:.2f}"
                ),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
            ).add_to(premium_layer)
        map_gas_prices.add_child(premium_layer)
        # Add the legend for premium prices
        premium_color_scale.add_to(map_gas_prices)

    # Add layer control to toggle between regular and premium layers
    folium.LayerControl().add_to(map_gas_prices)

    # Save map to HTML file
    map_gas_prices.save("./output/heatmap.html")
    print("Interactive map with toggleable layers and legends saved as 'gas_prices_toggle_layers_with_legends.html'. Open this file to view the map.")

plotTimeGraph(df)  
plotHeatMap(df)