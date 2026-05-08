"""
Punto di ingresso dell'applicazione Chainlit.

Questo modulo collega tre cose:
1. Chainlit -> fornisce l'interfaccia di chat nel browser
2. OpenAI    -> il modello GPT che ragiona e decide quali tool usare
3. Tools     -> la classe WeatherTool definita in tools.py

Il flusso e' il classico ciclo di "function calling":
- l'utente scrive un messaggio
- GPT decide se rispondere direttamente o chiamare uno dei nostri tool
- se chiama un tool, eseguiamo la funzione locale e gli restituiamo il risultato
- GPT formula una risposta finale in linguaggio naturale per l'utente
"""

import os
import json

import chainlit as cl
from openai import OpenAI
from dotenv import load_dotenv

from tools import WeatherTool


# Carica le variabili d'ambiente dal file .env (chiavi API, ecc.)
load_dotenv()

# Inizializza il client OpenAI usando la chiave letta dall'ambiente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Modello GPT da usare. gpt-4o-mini e' un buon compromesso costo/qualita'
MODEL = "gpt-4o-mini"

# Istanzio il tool una sola volta, all'avvio dell'app
weather_tool = WeatherTool()


# ---------------------------------------------------------------------------
# Definizione dei tool esposti al modello GPT.
#
# Questo array dichiara al modello QUALI funzioni puo' chiamare,
# COSA fanno (description) e QUALI parametri si aspettano.
# E' la "interfaccia" tra GPT e il nostro codice Python.
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": (
                "Restituisce il meteo corrente in una determinata localita'. "
                "L'utente deve specificare la citta'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Citta' ed eventualmente stato, es. 'Roma, IT'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Unita' di misura della temperatura",
                    },
                },
                "required": ["location"],
            },
        },
    },
]


def handle_tool_call(tool_call) -> str:
    """
    Esegue il tool richiesto da GPT e restituisce il risultato come stringa.

    GPT ci passa un oggetto `tool_call` che contiene:
    - il nome della funzione da chiamare
    - gli argomenti (in formato JSON)
    Noi mappiamo il nome alla classe giusta e ne invochiamo il metodo.
    """
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)

    # Log utile per debug: stampa cosa GPT sta chiamando e con quali argomenti
    print("*" * 80)
    print("function name:", function_name)
    print("function args:", function_args)
    print("*" * 80)

    # Smistamento verso il tool corretto
    if function_name == "get_current_weather":
        result = weather_tool.get_current_weather(**function_args)
    else:
        # Se GPT inventa un nome di funzione che non esiste, lo segnaliamo
        result = json.dumps({"error": f"Funzione sconosciuta: {function_name}"})

    print("result:", result)
    print("*" * 80)
    return result


def llm(messages):
    """
    Manda l'intera conversazione + la lista dei tool a OpenAI.
    Il parametro tool_choice="auto" lascia decidere al modello
    se rispondere direttamente o chiamare un tool.
    """
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )


# ---------------------------------------------------------------------------
# Hook Chainlit: viene eseguito ogni volta che si apre una nuova chat.
# ---------------------------------------------------------------------------
@cl.on_chat_start
def on_chat_start():
    # Inizializza la "cronologia" della conversazione con un messaggio di sistema
    # che spiega al modello che ruolo deve avere.
    cl.user_session.set("messages", [
        {
            "role": "system",
            "content": (
                "Sei un assistente meteo. Rispondi sempre in italiano, in modo "
                "conciso e amichevole.\n\n"
                "Regole operative:\n"
                "- Se l'utente specifica una città, chiama subito il tool "
                "  get_current_weather senza chiedere conferme.\n"
                "- Se l'utente non specifica una città, chiedigli di indicarla.\n"
                "- Non inventare mai i dati meteo: usa solo quelli restituiti dal tool."
            ),
        }
    ])


# ---------------------------------------------------------------------------
# Hook Chainlit: viene eseguito ad ogni messaggio inviato dall'utente.
# ---------------------------------------------------------------------------
@cl.on_message
async def main(message: cl.Message):
    # Recupera la cronologia accumulata fino ad ora dalla sessione
    messages = cl.user_session.get("messages")

    # Aggiunge il nuovo messaggio dell'utente alla cronologia
    messages.append({"role": "user", "content": message.content})

    # Ciclo di function calling: continua finche' GPT
    # non produce una risposta testuale finale per l'utente.
    while True:
        completion = llm(messages)
        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls

        # Caso 1: il modello ha rifiutato di rispondere (raro)
        if response_message.refusal:
            break

        # Caso 2: il modello ha prodotto una risposta testuale -> usciamo dal loop
        if response_message.content:
            messages.append(response_message)
            break

        # Caso 3: il modello vuole chiamare uno o piu' tool
        if tool_calls:
            # Aggiunge il messaggio dell'assistente (con i tool_calls) alla cronologia
            messages.append(response_message)

            # Per ogni tool richiesto, lo eseguiamo e accodiamo la sua risposta
            for tool_call in tool_calls:
                function_response = handle_tool_call(tool_call)
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": function_response,
                })
            # Poi torna in cima al while e GPT vede i risultati dei tool

    # Salva la cronologia aggiornata nella sessione utente
    cl.user_session.set("messages", messages)

    # Invia all'utente l'ultima risposta dell'assistente
    await cl.Message(
        author="assistant",
        content=messages[-1].content,
    ).send()