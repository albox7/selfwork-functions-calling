"""
Modulo che contiene le classi-tool usate dal function calling di OpenAI.

Ogni classe rappresenta un "tool" che il modello GPT puo' decidere di invocare:
- WeatherTool -> recupera il meteo corrente da un'API meteo esterna
"""

import os
import json
import requests


class WeatherTool:
    """
    Tool per ottenere il meteo corrente di una citta'.

    Supporta due provider:
    - OpenWeatherMap (https://openweathermap.org/)
    - WeatherAPI     (https://www.weatherapi.com/)

    Le chiavi API vengono lette dalle variabili d'ambiente
    (OPENWEATHERMAP_KEY e WEATHERAPI_KEY), caricate dal file .env.
    """

    def __init__(self):
        # Recupero le chiavi API dalle variabili d'ambiente.
        # Se non sono presenti, le richieste falliranno con un errore HTTP.
        self.openweathermap_key = os.getenv("OPENWEATHERMAP_KEY")
        self.weatherapi_key = os.getenv("WEATHERAPI_KEY")

    def get_weather_openweathermap(self, city: str) -> str:
        """Recupera il meteo da OpenWeatherMap e restituisce un JSON."""
        # Endpoint del servizio "current weather"
        base_url = "http://api.openweathermap.org/data/2.5/weather"

        # Parametri della query string:
        # - q     : nome della citta' (es. "Roma, IT")
        # - appid : la nostra API key
        # - units : "metric" -> temperature in gradi Celsius
        # - lang  : risposta tradotta in italiano
        params = {
            "q": city,
            "appid": self.openweathermap_key,
            "units": "metric",
            "lang": "it",
        }

        # Chiamata HTTP GET al servizio meteo
        response = requests.get(base_url, params=params)

        # Se la risposta non e' 200 (OK), restituisco un messaggio di errore
        if response.status_code != 200:
            return f"Errore nel recupero dei dati meteo: {response.status_code}"

        # Parso la risposta JSON e estraggo solo i campi che ci interessano
        data = response.json()
        return json.dumps({
            "source": "openweathermap",
            "city": city,
            "description": data["weather"][0]["description"],
            "temperature_c": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "wind_speed_ms": data["wind"]["speed"],
        })

    def get_weather_weatherapi(self, city: str) -> str:
        """Recupera il meteo da WeatherAPI e restituisce un JSON."""
        # Endpoint del servizio "current weather"
        base_url = "http://api.weatherapi.com/v1/current.json"

        # Parametri della query string:
        # - key : la nostra API key
        # - q   : nome della citta'
        # - aqi : "no" -> non includere dati sulla qualita' dell'aria
        params = {
            "key": self.weatherapi_key,
            "q": city,
            "aqi": "no",
        }

        # Try/except: gestisce sia errori di rete sia status code non validi
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Solleva eccezione se status != 2xx
            data = response.json()

            # Estraggo solo i campi che servono al modello
            return json.dumps({
                "source": "weatherapi",
                "city": data["location"]["name"],
                "country": data["location"]["country"],
                "temperature_c": data["current"]["temp_c"],
                "condition": data["current"]["condition"]["text"],
                "humidity": data["current"]["humidity"],
                "wind_kmh": data["current"]["wind_kph"],
            })
        except requests.exceptions.RequestException as e:
            return f"Errore: {str(e)}"

    def get_current_weather(self, location: str, unit: str = "celsius") -> str:
        """
        Metodo "pubblico" invocato dal function calling di OpenAI.

        Il modello GPT non chiama direttamente le funzioni dei singoli provider:
        chiama questo metodo, che decide internamente quale provider usare.
        Cosi' possiamo cambiare backend senza modificare la logica del chatbot.
        """
        # Per default uso WeatherAPI; in caso di problemi si puo' cambiare
        # con self.get_weather_openweathermap(location)
        return self.get_weather_weatherapi(location)

