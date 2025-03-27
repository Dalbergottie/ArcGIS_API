import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from arcgis.features import GeoAccessor
from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection

# Objective: This script automates the preparation, analysis, and visualization of geospatial data.
# Fetch or ingest desired data.
# Fire data from NASA is filtered to only include records in Brazil, Peru, and Bolivia.
# Publish to ArcGIS Online (or Portal for ArcGIS).

# Define Constants
FIRE_DATA_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_South_America_7d.csv"
COUNTRIES_URL = "https://hub.arcgis.com/datasets/esri::world-countries-generalized.geojson"
COUNTRIES_TO_KEEP = ["Brazil", "Peru", "Bolivia"]

# ArcGIS Online Credentials (Replace with your own)
PORTAL_URL = "https://daniele.maps.arcgis.com/home/content.html"  # Change for Enterprise Portal
USERNAME = "" # Put credentials here
PASSWORD = "" # Put credentials here
ITEM_TITLE = "Filtered Fire Data - Brazil, Peru, Bolivia"


def fetch_fire_data():
    """Download the latest active fire data."""
    print("Fetching fire data...")
    fire_df = pd.read_csv(FIRE_DATA_URL)
    fire_df["geometry"] = fire_df.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)

    return gpd.GeoDataFrame(fire_df, geometry="geometry", crs="EPSG:4326")


def fetch_country_boundaries():
    """Fetch world country boundaries and filter for selected countries."""
    print("Fetching country boundaries...")
    response = requests.get(COUNTRIES_URL)
    response.raise_for_status()

    world_gdf = gpd.read_file(response.text)
    world_gdf = world_gdf[world_gdf["COUNTRY"].isin(COUNTRIES_TO_KEEP)]

    return world_gdf


def filter_fire_data(fire_gdf, countries_gdf):
    """Filter fire data to include only points within Brazil, Peru, and Bolivia."""
    print("Filtering fire data...")
    filtered_gdf = gpd.sjoin(fire_gdf, countries_gdf, how="inner", predicate="within")

    return filtered_gdf.drop(columns=["index_right"])  # Remove extra index from spatial join


def publish_to_arcgis(filtered_gdf):
    """Upload and publish the dataset to ArcGIS Portal."""
    print("Publishing to ArcGIS Online...")

    gis = GIS(PORTAL_URL, USERNAME, PASSWORD)

    # Convert GeoDataFrame to Esri-supported format
    sdf = GeoAccessor.from_geodataframe(filtered_gdf)

    # Search for existing item
    existing_items = gis.content.search(ITEM_TITLE, item_type="Feature Layer")
    if existing_items:
        print("Updating existing layer...")
        item = existing_items[0]
        flc = FeatureLayerCollection.fromitem(item)
        flc.manager.overwrite(sdf)
    else:
        print("Creating a new feature layer...")
        sdf.spatial.to_featurelayer(title=ITEM_TITLE, gis=gis)

    print("Publishing complete!")


if __name__ == "__main__":
    try:
        fire_gdf = fetch_fire_data()
        countries_gdf = fetch_country_boundaries()
        filtered_gdf = filter_fire_data(fire_gdf, countries_gdf)

        print(f"Filtered {len(filtered_gdf)} fire records.")
        publish_to_arcgis(filtered_gdf)

        print("Process completed successfully!")
    except Exception as e:
        print(f"Error: {e}")

