from shiny.express import input, render, ui
from shiny import reactive, render
import ipyleaflet as ipyl
from shinywidgets import render_widget
import pandas as pd

import openmeteo_requests
import requests_cache
from retry_requests import retry

import matplotlib.pyplot as plt
import numpy as np


# Webpage
ui.page_opts(title = "Heat Pump Efficacy Dashboard", fillable=True)

cities = pd.read_csv("data/cities.csv")

cs_to_coords = cities.set_index("city_state").T.to_dict("list")
city_states = dict(zip(cities["city_state"], cities["city_state"]))

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://archive-api.open-meteo.com/v1/archive"
uiuc_lat, uiuc_lng = cs_to_coords["Urbana, Illinois"]

params = {
    "latitude": uiuc_lat,               # input
    "longitude": uiuc_lng,              # input
    "start_date": "2022-01-01",      # input
    "end_date": "2024-01-01",        # input
    "daily": "temperature_2m_min",   # fixed
    "temperature_unit": "fahrenheit" # input
}
responses = openmeteo.weather_api(url, params=params)

# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]

# Process daily data. The order of variables needs to be the same as requested.
daily = response.Daily()
daily_temperature_2m_min = daily.Variables(0).ValuesAsNumpy()

daily_data = {"date": pd.date_range(
    start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
    end = pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
    freq = pd.Timedelta(seconds = daily.Interval()),
    inclusive = "left"
)}
daily_data["temperature_2m_min"] = daily_temperature_2m_min

daily_dataframe = pd.DataFrame(data = daily_data)

with ui.sidebar(bg="#f8f8f8", open="always", width="350px"):

    ui.input_select("city", "City", choices=city_states, selected="Urbana, Illinois")

    @render.text()
    def text():
        lat, lng = cs_to_coords[input.city()]
        return f"{lat}\xb0N, {lng}\xb0E"

    ui.input_date_range("daterange", "Dates", start="2022-01-01", end="2024-01-01", min="2020-01-01", max="2024-01-01")

    ui.input_radio_buttons(
        "units",
        "Units",
        {"fahrenheit": "Fahrenheit", "celsius": "Celsius"}
    )

    ui.input_slider("plottemp", "Plot Temperature", min=-15, max=50, value=5)

    ui.input_checkbox_group(
        "options",
        "Plot Options",
        {"week": "Weekly Rolling Average", "month":"Monthly Rolling Average"}
    )

    ui.input_slider("tabletemp", "Table Temperature", min=-25, max=60, value=[0, 15])

    @render_widget
    def map():
        coord = cs_to_coords[input.city()]
        map = ipyl.Map(center=coord)
        mark = ipyl.Marker(location=coord, draggable=False)
        map.add_layer(mark)
        return map
    
    @reactive.effect
    def _():

        # Convert to celsius
        if "celsius" in input.units():
            ui.update_slider("plottemp", min=-25, max=10, value=-15)
            ui.update_slider("tabletemp", min=-30, max=15, value=[-20, -10])

        # Convert to fahrenheit
        if "fahrenheit" in input.units():
            ui.update_slider("plottemp", min=-15, max=50, value=5)
            ui.update_slider("tabletemp", min=-25, max=60, value=[0, 15])
        

with ui.navset_underline():

    @reactive.calc()
    def data():
        # Make sure all required weather variables are listed here
        # The order of variables in hourly or daily is important to assign them correctly below
        lat, lng = cs_to_coords[input.city()]
        sday, eday = input.daterange()
        unit = input.units()
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,               # input
            "longitude": lng,              # input
            "start_date": sday,      # input
            "end_date": eday,        # input
            "daily": "temperature_2m_min",   # fixed
            "temperature_unit": unit # input
        }
        responses = openmeteo.weather_api(url, params=params)

        # Process first location. Add a for-loop for multiple locations or weather models
        response = responses[0]

        # Process daily data. The order of variables needs to be the same as requested.
        daily = response.Daily()
        daily_temperature_2m_min = daily.Variables(0).ValuesAsNumpy()

        daily_data = {"date": pd.date_range(
            start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
            end = pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = daily.Interval()),
            inclusive = "left"
        )}
        daily_data["temperature_2m_min"] = daily_temperature_2m_min

        daily_dataframe = pd.DataFrame(data = daily_data)

        stable, etable = input.tabletemp()
        temps =  np.arange(etable, stable - 1, -1)
        daily_temps = daily_dataframe["temperature_2m_min"]
        days_below = [np.sum(daily_temps < t) for t in temps]
        tot_days = daily_temps.size
        prop_below = [round(d/tot_days,3) for d in days_below]
        temp_tab = {"Temp": temps, "Days Below": days_below, "Proportion Below": prop_below}

        tabled = pd.DataFrame(data=temp_tab)

        return daily_dataframe, tabled

    with ui.nav_panel("Historical"):
        @render.plot
        def hist():
            dat = data()[0]
            daily_temps = dat["temperature_2m_min"]
            plt.xlabel("Date Range")
            if "celsius" in input.units():
                plt.ylabel("Daily Minimum Temprature \xb0C")
            else:
                plt.ylabel("Daily Minimum Temprature \xb0F")

            colors = np.where(daily_temps < input.plottemp(), "0.8", "k")
        
            plt.scatter(dat["date"], daily_temps, color=colors, s=10, zorder=3)
            
            plt.axhline(y=input.plottemp(), color="dimgray")

            plt.grid(color="lightgray", zorder=0)

            if "week" in input.options():
                week_avgs = daily_temps.rolling(window=7, center=True).mean()
                plt.plot(dat["date"], week_avgs, color="tab:orange")
        
            if "month" in input.options():
                month_avgs = daily_temps.rolling(window=30, center=True).mean()
                plt.plot(dat["date"], month_avgs)


        @render.data_frame
        def table():
            return render.DataGrid(data=data()[1], width="100%", height="auto")

    with ui.nav_panel("About"):
        ui.markdown(
            """

            ## **Context**

            <br/>

            Heat Pump Efficacy Dashboard is an **interactive dashboard** that helps determine <br>
            the effectiveness of installing heat pumps in a particular location in the US <br>
            depending on the severity of the weather.

            The historical tab contains:
            - A graph that displays the daily minimum temperatures within a specified date range.
            - A table that displays:
                - **Temp** - The range of selected temperatures from Table Temperature.
                - **Days Below** - Number of days where daily minimum temperature <= respective temperature.
                - **Proportion Below** - Ratio of days below to total number of days in date range.
            <br/>
            <br/>
            
            ## **Usage Instructions/Information**

            <br/>

            _Edit the options in the sidebar to the left to reactively update the graph and table_
            <br/>

            City
            - Select a **city** as the place of interest
            - Displays the city's **latitude** and **longitude**

            Dates
            - Select a **start date** and **end date** to see all daily minimum temperatures in between the date range

            Units
            - Select preferred units of **fahrenheit** or **celsius**

            Plot Temperature
            - Select a temperature to graphically **separate** the daily minimum temperatures above and below the specified temperature

            Plot Options
            - Select **weekly rolling average** to display the weekly rolling average of the daily minimum temperatures
            - Select **monthly rolling average** to display the monthly rolling average of the daily minimum temperatures
            
            Table Temperature
            - Select a temperature range to **tabulate** days below and proportion below for all integer temperatures in the range
            
            Map
            - **Interactive map** that displays the location of the selected city above
            
            <br/>
    
            #### **Data Sources**
            > Location Data - [SimpleMaps](https://simplemaps.com/data/us-cities)
            >
            > Weather Data - [Open Meteo](https://open-meteo.com/)

            """
        )
