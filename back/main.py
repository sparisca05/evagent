from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
import random

app = FastAPI()

# Permitir CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/", response_class=HTMLResponse)
async def post():
    

# Cargar variables de entorno
load_dotenv()
GEMINI_API_KEY = os.getenv("API_KEY")

# Configurar Google Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


historial = [
    {
        "role": "system",
        "content":
            """Your name is Eva, you are an AI Agent that works for a company that 
            is attempting to find their potential clients inside a huge event. 
            
            An excel sheet with a 'linkedindUrl' column will be provided by the user 
            and you will filter the users based on their profles, looking for their 
            personal and professional information and share their possible preferences
            based on that information."""},
]

# Iniciar conversación por consola
print("💬 Chatbot de Negociación de Pagos (Escribe 'salir' para terminar)\n")

respuesta = 0

def inferContext(mensaje):
    historial.append({"role": "system", "content": "Define a cuál de las siguientes opciones: 1.Ampliar cuotas 2.Reducir montos 3.Disminuir intereses 4.Otra. Se refiere este mensaje: " + mensaje + " y dame una respuesta con una solución propuesta."})
    response = model.generate_content([m["content"] for m in historial])
    return response

while True:
    user_input = input("Tú: ")
    if user_input.lower() == "salir":
        print("👋 Adiós!")
        break

    respuesta += 1

    # Agregar input del usuario al historial
    historial.append({"role": "user", "content": user_input})
    
    if respuesta == 1:
        # Generar valores aleatorios para crédito y días de mora
        credito = str(random.randint(100, 300) * 10000)
        dias = str(random.randint(10, 90))
        
        historial.append({"role": "context", "content": "proporciona al usuario una respuesta basada en estos ejemplos (separados por ;) y teniendo en cuenta que el crédito es " + credito + " y los dias en mora " + dias + ": " + pdf.train()} )
        response = model.generate_content([m["content"] for m in historial])
        historial.append({"role": "assistant", "content": response.text})
        print(f"Isabot: {response.text}")
    elif respuesta == 2:
        # Inferir contexto
        response = inferContext(user_input)
        historial.append({"role": "system", "content": "Responde al cliente basado en esta respuesta: " + response.text})
        print(f"Isabot: {response.text}")
    else: 
        # Enviar historial completo a la IA
        response = model.generate_content([m["content"] for m in historial])
        
        # Agregar respuesta de la IA al historial
        historial.append({"role": "assistant", "content": response.text})
        print(f"Isabot: {response.text}")