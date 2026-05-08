# Selfwork — Functions Calling con OpenAI

Mini-progetto didattico che implementa un **assistente meteo conversazionale** usando il *function calling* delle API OpenAI e [Chainlit](https://docs.chainlit.io/) come interfaccia di chat.

L'utente scrive in linguaggio naturale (es. *"Che tempo fa a Madrid?"*); il modello GPT decide autonomamente di chiamare la funzione `get_current_weather`, che a sua volta interroga il servizio [WeatherAPI](https://www.weatherapi.com/) (in alternativa è disponibile un'implementazione per [OpenWeatherMap](https://openweathermap.org/)). Il risultato viene poi sintetizzato dal modello in una risposta amichevole.

## Stack

- **Python** ≥ 3.10, < 3.14
- **Poetry** per la gestione delle dipendenze e del virtualenv
- **OpenAI Python SDK** (`openai`)
- **Chainlit** per la UI di chat
- **python-dotenv** per la gestione delle variabili d'ambiente
- **requests** per le chiamate HTTP ai servizi meteo

## Struttura del progetto

```
selfwork-functions-calling/
├── pyproject.toml          # configurazione Poetry e dipendenze
├── poetry.lock             # lock file delle dipendenze
├── .env.example            # template delle variabili d'ambiente
├── .gitignore
├── README.md
├── chainlit.md             # pagina di benvenuto Chainlit
└── weather/
    ├── __init__.py         # entry point Chainlit + loop di function calling
    └── tools.py            # classe WeatherTool (chiamate alle API meteo)
```

## Setup

### 1. Clona il repository

```bash
git clone git@github.com:albox7/selfwork-functions-calling.git
cd selfwork-functions-calling
```

### 2. Installa le dipendenze

```bash
poetry install
```

### 3. Configura le variabili d'ambiente

Copia il file di esempio e inserisci le tue chiavi:

```bash
cp .env.example .env
```

Poi apri `.env` con un editor e inserisci i valori reali per:

- `OPENAI_API_KEY` — ottenibile su https://platform.openai.com/api-keys
- `WEATHERAPI_KEY` — ottenibile su https://www.weatherapi.com/
- `OPENWEATHERMAP_KEY` — opzionale, ottenibile su https://openweathermap.org/api

## Avvio

```bash
poetry run chainlit run weather/__init__.py -w
```

L'app si apre automaticamente nel browser su `http://localhost:8000`.

Il flag `-w` attiva la modalità *watch*: ogni modifica ai file Python ricarica l'app.

## Esempi di utilizzo

- *"Che tempo fa a Roma?"*
- *"Mi dici il meteo di Tokyo?"*
- *"Quanti gradi ci sono a New York adesso?"*

Se non specifichi una città, l'assistente te la chiederà.

## Come funziona il function calling

1. L'utente invia un messaggio
2. Il backend manda a OpenAI: messaggio + descrizione dei tool disponibili
3. GPT decide se rispondere direttamente o invocare un tool
4. Se invoca un tool, il backend lo esegue (chiamata reale a WeatherAPI) e restituisce il risultato a GPT
5. GPT formula la risposta finale in linguaggio naturale

Tutto il loop è implementato nella funzione `main` di `weather/__init__.py`.