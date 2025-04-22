import os
from dotenv import load_dotenv
import re
import asyncio
import json

from typing import Annotated, List, Dict, Any
from openai import AsyncOpenAI
from apify_client import ApifyClient

from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents import ChatHistory
from semantic_kernel.agents import ChatCompletionAgent, AgentGroupChat
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)

from semantic_kernel.functions import KernelFunctionFromPrompt
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
from semantic_kernel.functions import KernelArguments, kernel_function

# Azure imports for project client and credentials
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, FilePurpose, ToolSet
from azure.identity import InteractiveBrowserCredential

# Semantic Kernel imports
from semantic_kernel.agents.azure_ai import AzureAIAgent

# Load environment variables from .env file
load_dotenv()

# Configurar AIProjectClient
project_client = AIProjectClient.from_connection_string(
    credential=InteractiveBrowserCredential(),
    conn_str=os.environ["PROJECT_CONNECTION_STRING"],
)

# Crear un kernel para manejar las funciones y servicios
kernel = Kernel()

# Definir una función simple para probar
@kernel_function(
    name="get_current_weather",
    description="Obtiene el clima actual para una ubicación dada",
)
def get_current_weather(location: str) -> str:
    # Esta es una implementación simulada para pruebas
    return f"El clima en {location} es soleado y 25°C"

# Registrar la función en el kernel
kernel.add_function(get_current_weather)

# Crear y configurar el agente de Azure AI
async def create_and_test_agent():
    # Crear un agente con Azure AI
    agent = await AzureAIAgent.create(
        project_client=project_client,
        project_id=os.environ.get("PROJECT_ID"),
        deployment_name=os.environ.get("DEPLOYMENT_NAME", "default"),
        kernel=kernel
    )
    
    # Crear un historial de chat para la conversación
    chat_history = ChatHistory()
    
    # Añadir un mensaje de sistema para establecer el comportamiento del agente
    chat_history.add_system_message("Eres un asistente útil que puede responder preguntas y realizar tareas.")
    
    # Añadir una pregunta del usuario
    chat_history.add_user_message("¿Cuál es el clima en Madrid?")
    
    # Obtener una respuesta del agente
    response = await agent.chat_invoke_async(chat_history)
    
    # Imprimir la respuesta
    print("Respuesta del agente:")
    print(response.value)
    
    return response

# Función principal para ejecutar el código de prueba
if __name__ == "__main__":
    print("Iniciando prueba del agente de Azure AI...")
    asyncio.run(create_and_test_agent())
    print("Prueba completada.")
