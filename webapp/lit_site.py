# ------------------------------------------------------------
# IMPORTS AND LIBRARIES
# ------------------------------------------------------------

import pandas as pd
import numpy as np
import streamlit as st
import geopandas
import folium
    
import plotly.express as px

from datetime import datetime, time
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster

# ------------------------------------------------------------
# FUNCTION DEFS
# ------------------------------------------------------------
@st.cache(allow_output_mutation=True)
def get_data(path):
    data = pd.read_csv(path)
    data["date"] = pd.to_datetime(data["date"])

    return data


@st.cache(allow_output_mutation=True)
def get_geofile(url):
    geofile = geopandas.read_file(url)

    return geofile


def add_columns(data):
    data["price_ft2"] = data["price"] / data["sqft_lot"]
    data["date"] = pd.to_datetime(data["date"]).dt.strftime("%Y-%m-%d")

    return data


def avg_metrics(data):
    df1 = data[["id", "zipcode"]].groupby("zipcode").count().reset_index()
    df2 = data[["zipcode", "price"]].groupby("zipcode").mean().reset_index()
    df3 = data[["zipcode", "sqft_living"]].groupby("zipcode").mean().reset_index()
    df4 = data[["zipcode", "price_ft2"]].groupby("zipcode").mean().reset_index()

    m1 = pd.merge(df1, df2, on="zipcode", how="inner")
    m2 = pd.merge(m1, df3, on="zipcode", how="inner")
    df = pd.merge(m2, df4, on="zipcode", how="inner")

    df.columns = ["ZIPCODE", "TOTAL HOUSES", "PRICE", "SQFT_LIVING", "PRICE/FT2"]

    return df


def descriptive_data(data):
    num_attributes = data.select_dtypes(include=["int64", "float64"])
    media = pd.DataFrame(num_attributes.apply(np.mean))
    mediana = pd.DataFrame(num_attributes.apply(np.median))
    std = pd.DataFrame(num_attributes.apply(np.std))

    max_ = pd.DataFrame(num_attributes.apply(np.max))
    min_ = pd.DataFrame(num_attributes.apply(np.min))

    df1 = pd.concat([max_, min_, media, mediana, std], axis=1).reset_index()
    df1.columns = ["Attributes", "max", "min", "mean", "median", "std"]

    return df1


def data_overview(data, f_zipcode, f_columns):
    st.title("Data Overview")

    if (f_zipcode != []) & (f_columns != []):
        data = data.loc[data["zipcode"].isin(f_zipcode), f_columns]

    elif (f_zipcode != []) & (f_columns == []):
        data = data.loc[data["zipcode"].isin(f_zipcode), :]

    elif (f_zipcode == []) & (f_columns != []):
        data = data.loc[:, f_columns]

    elif (f_zipcode == []) & (f_columns == []):
        data = data.copy()

    st.dataframe(data)

    return None


def region_overview(data, geofile):
    c3, c4 = st.columns((1, 1))

    c3.header("Portfolio Density")
    df = data.sample(
        1000
    )  # Aqui, é utilizado a amostragem apenas para rodar o código + rápido ;)

    density_map = folium.Map(
        location=[data["lat"].mean(), data["long"].mean()], default_zoom_start=15
    )

    marker_cluster = MarkerCluster().add_to(density_map)
    for name, row in df.iterrows():
        folium.Marker(
            [row["lat"], row["long"]],
            popup="Sold R${0} on {1}. Features: {2} sqft, {3} bedrooms, {4} bathrooms, year built: {5}".format(
                row["price"],
                row["date"],
                row["sqft_living"],
                row["bedrooms"],
                row["bathrooms"],
                row["yr_built"],
            ),
        ).add_to(marker_cluster)

    with c3:
        folium_static(density_map)

    # Region Price Map
    c4.header("Price Density")

    df = data[["price", "zipcode"]].groupby("zipcode").mean().reset_index()
    df.columns = ["ZIP", "PRICE"]
    df = df.sample(60)

    geofile = geofile[geofile["ZIP"].isin(df["ZIP"].tolist())]

    region_price_map = folium.Map(
        location=[data["lat"].mean(), data["long"].mean()], default_zoom_start=15
    )

    region_price_map.choropleth(
        data=df,
        geo_data=geofile,
        columns=["ZIP", "PRICE"],
        key_on="feature.properties.ZIP",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="AVG PRICE",
    )

    with c4:
        folium_static(region_price_map)

    return None


def price_variation(data, f_anual, f_daily):
    # Anual Variation
    st.header("Anual Price Variation")

    df = data[["price", "yr_built"]].groupby("yr_built").mean().reset_index()

    df = df.loc[df["yr_built"] < f_anual]

    fig = px.line(df, x="yr_built", y="price")
    st.plotly_chart(fig, use_container_width=True)

    # Daily Variation
    st.header("Daily Price Variation")

    data["date"] = pd.to_datetime(data["date"])
    df = data[["price", "date"]].groupby("date").mean().reset_index()
    df = df.loc[df["date"] < f_daily]

    fig = px.line(df, x="date", y="price")
    st.plotly_chart(fig, use_container_width=True)

    return None


def attributes_distribution(
    data, f_price_hist, f_bedrooms_hist, f_bathrooms_hist, f_floors, f_waterview
):
    st.header("Attributes Distribution")

    df = data[["price", "bedrooms", "bathrooms", "floors", "waterfront"]]

    c5, c6 = st.columns((1, 1))

    # Price Distribution
    df = df.loc[df["price"] < f_price_hist]
    fig = px.histogram(df, x="price", nbins=50)
    c5.header("Price Distribution")
    c5.plotly_chart(fig, use_container_width=True)

    # Bedrooms Distribution
    df = df.loc[df["bedrooms"] < f_bedrooms_hist]
    fig = px.histogram(df, x="bedrooms", nbins=10)
    c6.header("Bedroom Distribution")
    c6.plotly_chart(fig, use_container_width=True)

    # Bathrooms Distribution

    c7, c8 = st.columns((1, 1))

    df = df.loc[df["bathrooms"] < f_bathrooms_hist]
    fig = px.histogram(df, x="bathrooms", nbins=10)
    c7.header("Bathroom Distribution")
    c7.plotly_chart(fig, use_container_width=True)

    # Floors Distribution

    df = df.loc[df["floors"] < f_floors]
    fig = px.histogram(df, x="floors", nbins=10)
    c8.header("Floors Distribution")
    c8.plotly_chart(fig, use_container_width=True)

    # Waterview

    df = data[data["waterfront"] < f_waterview]
    if f_waterview:
        df = data[data["waterfront"] == 1]
    else:
        df = data.copy()

    fig = px.histogram(df, x="waterfront", nbins=2)
    st.header("Houses per water view")
    st.plotly_chart(fig, use_container_width=True)

    return None


def create_filter(data):
    f_zipcode = st.sidebar.multiselect("Region Select", data["zipcode"].unique())

    f_columns = st.sidebar.multiselect("Select Attributes", data.columns)

    min_year = int(data["yr_built"].min())
    max_year = int(data["yr_built"].max())
    f_anual = st.sidebar.slider("Anual Price Variation", min_year, max_year, min_year)

    min_date = datetime.strptime(data["date"].min(), "%Y-%M-%d")
    max_date = datetime.strptime(data["date"].max(), "%Y-%M-%d")
    f_daily = st.sidebar.slider("Daily Price Variation", min_date, max_date, min_date)

    min_price = int(data["price"].min())
    max_price = int(data["price"].min())
    avg_price = int(data["price"].mean())
    f_price_hist = st.sidebar.slider(
        "Price Distribution", min_price, max_price, avg_price
    )

    f_bedrooms_hist = st.sidebar.selectbox(
        "Max Number of Bedrooms", sorted(set(data["bedrooms"].unique()))
    )
    f_bathrooms_hist = st.sidebar.selectbox(
        "Max Number of Bathrooms", sorted(set(data["bathrooms"].unique()))
    )
    f_floors = st.sidebar.selectbox(
        "Max Number of Floors", sorted(set(data["floors"].unique()))
    )
    f_waterview = st.sidebar.checkbox("Has Waterview?")

    return (
        f_zipcode,
        f_columns,
        f_anual,
        f_daily,
        f_price_hist,
        f_bedrooms_hist,
        f_bathrooms_hist,
        f_floors,
        f_waterview,
    )


# ------------------------------------------------------------
# SITE LAYOUT AND APPLICATION
# ------------------------------------------------------------

if __name__ == "__main__":
    st.set_page_config(layout="wide")

    st.title("House Rocket Co.")
    st.markdown("Welcome to House Rocket Data Analysis")

    st.header("Region Filter")

    path = "webapp/kc_house_data.csv"
    df = get_data(path)
    data = add_columns(df)

    url = "webapp/Zip_Codes.geojson"
    geofile = get_geofile(url)

    (
        f_zipcode,
        f_columns,
        f_anual,
        f_daily,
        f_price_hist,
        f_bedrooms_hist,
        f_bathrooms_hist,
        f_floors,
        f_waterview,
    ) = create_filter(data)

    data_overview(data, f_zipcode, f_columns)

    # Average metrics for total number of houses

    c1, c2 = st.columns((1, 1))

    df = avg_metrics(data)
    c1.header("Average Metrics")
    c1.dataframe(df, width=600)

    # Descriptive Statistics

    df1 = descriptive_data(data)
    c2.header("Descriptive Analysis")
    c2.dataframe(df1, width=600)

    # Portfolio Density

    region_overview(data, geofile)

    # Price Variation

    price_variation(data, f_anual, f_daily)

    # House Distribution

    attributes_distribution(
        data, f_price_hist, f_bedrooms_hist, f_bathrooms_hist, f_floors, f_waterview
    )
