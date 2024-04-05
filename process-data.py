import pandas as pd

# Read csv
df = pd.read_csv("data-raw/uscities.csv")

# Remove duplicates and filter by population >= 10000
df = df.drop_duplicates().loc[df["population"] >= 10000]

# Create city_state column
df["city_state"] = df["city"] + ", " + df["state_name"]

# Create new dataframe with city_state, lat, lng
clean = df.filter(["city_state", "lat", "lng"])

# Save to new csv
clean.to_csv("data/cities.csv", index=False)
