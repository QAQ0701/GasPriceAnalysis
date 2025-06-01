import pandas as pd

# Load the Excel file
file_path = "./data/gas_prices.xlsx"  # Change if needed
df = pd.read_excel(file_path)

# Convert 'Query Time' to datetime FIRST
df['Query Time'] = pd.to_datetime(df['Query Time'], errors='coerce')

# Drop rows where 'Query Time' couldn't be parsed
df = df.dropna(subset=['Query Time'])

# Remove rows with both Regular and Premium prices missing
df = df.dropna(subset=['Regular Price', 'Premium Price'], how='all')

# Add 'Time Tag' column based on the hour of 'Query Time'
def tag_time(hour):
    if 8 <= hour < 10:
        return 'morning'
    elif 12 <= hour < 15:
        return 'afternoon'
    elif 19 <= hour < 22:
        return 'evening'
    elif 4 <= hour < 5:
        return 'midnight'
    else:
        return 'other'

df['Time Tag'] = df['Query Time'].dt.hour.apply(tag_time)

# Extract the date part for deduplication
df['Query Date'] = df['Query Time'].dt.normalize()

# Drop duplicates based on Station ID, Time Tag, and Query Date
df = df.drop_duplicates(subset=['Station ID', 'Time Tag', 'Query Date'])

# Sort by Station ID
df = df.sort_values(by='Station ID')

# Save to Excel
df.to_excel("./data/cleaned_gas_prices.xlsx", index=False)

# Preview
print(df[['Station ID', 'Query Time', 'Time Tag']].head())
