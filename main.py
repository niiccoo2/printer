import os
os.makedirs(os.path.expanduser("~/.cache/escpos"), exist_ok=True)
os.environ.setdefault("ESCPOS_CAPABILITIES_PICKLE_DIR", os.path.expanduser("~/.cache/escpos"))

from escpos.printer import Usb
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import datetime
import locale
import time

locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")



numbers = {1:"prima", 2:"due", 3:"tre", 4:"quattro", 5:"cinque", 6:"sei", 7:"sette", 8:"otto", 9:"nove", 10:"dieci", 11:"undici", 12:"dodici", 13:"tredici", 14:"quattordici", 15:"quindici", 16:"sedici", 17:"diciassette", 18:"diciotto", 19:"diciannove", 20:"venti", 21:"ventuno", 22:"venidue", 23:"venitre", 24:"ventiquattro", 25:"venticinque", 26:"ventisei", 27:"ventisette", 28:"ventotto", 29:"ventinove", 30:"trenta", 31:"trentuno"}

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": 42.3584,
	"longitude": -71.0598,
	"daily": ["sunrise", "sunset", "temperature_2m_max", "temperature_2m_min", "precipitation_probability_max"],
	"timezone": "auto",
	"forecast_days": 1,
	"wind_speed_unit": "mph",
	"temperature_unit": "fahrenheit",
	"precipitation_unit": "inch",
}

last_printed = None

def create_printer_object():
	return Usb(0x04b8, 0x0e28, 0, profile="TM-T20II")

def create_formatted_date():
	date = datetime.datetime.now()
    
	day_name_list = list(date.strftime("%A"))
	day_name_list[0] = day_name_list[0].upper()

	return date.strftime(f"{''.join(day_name_list)}, {numbers[date.day]} %B")

def print_daily_paper():
	print("Printing daily paper!")

	p = create_printer_object()

	try:
		response = openmeteo.weather_api(url, params = params)[0]

		# Process daily data. The order of variables needs to be the same as requested.
		daily = response.Daily()
		daily_sunrise = daily.Variables(0).ValuesInt64AsNumpy()
		daily_sunset = daily.Variables(1).ValuesInt64AsNumpy()
		daily_temperature_2m_max = daily.Variables(2).ValuesAsNumpy()
		daily_temperature_2m_min = daily.Variables(3).ValuesAsNumpy()
		daily_precipitation_probability_max = daily.Variables(4).ValuesAsNumpy()

		daily_data = {
			"date": pd.date_range(
				start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
				end =  pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
				freq = pd.Timedelta(seconds = daily.Interval()),
				inclusive = "left"
			).tz_convert(response.Timezone().decode())
		}

		daily_data["sunrise"] = pd.to_datetime(daily_sunrise, unit = "s", utc = True).tz_convert(response.Timezone().decode())
		daily_data["sunset"] = pd.to_datetime(daily_sunset, unit = "s", utc = True).tz_convert(response.Timezone().decode())
		daily_data["temperature_2m_max"] = daily_temperature_2m_max
		daily_data["temperature_2m_min"] = daily_temperature_2m_min
		daily_data["precipitation_probability_max"] = daily_precipitation_probability_max



		p.textln(create_formatted_date())
		p.textln()
		p.textln(f"High: {round(daily_data["temperature_2m_max"][0])}° Low: {round(daily_data["temperature_2m_min"][0])}°")
		p.textln(f"Sunrise: {daily_data["sunrise"].strftime("%H:%M")[0]} Sunset: {daily_data["sunset"].strftime("%H:%M")[0]}")
		p.text(f"Precipitation: {round(daily_data["precipitation_probability_max"][0])}%")
		p.cut()
	finally:
		p.close()

def init_printer():
	p = create_printer_object()

	p.set_with_default(align="center")

	p.close()

init_printer()

while True:
	now = datetime.datetime.now()

	if now.date() != last_printed and now.hour >= 6: # I understand that this is kinda a bad way to do it, but it works...
		print_daily_paper()
		last_printed = now.date()
	time.sleep(60)