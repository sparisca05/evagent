import os
from dotenv import load_dotenv

import random
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from typing import Annotated, List, Dict
from openai import AsyncOpenAI
from apify_client import ApifyClient

from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatHistory

from semantic_kernel.agents.open_ai import OpenAIAssistantAgent
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from semantic_kernel.functions import kernel_function

from semantic_kernel.connectors.ai import FunctionChoiceBehavior

from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
from semantic_kernel.functions import KernelArguments, kernel_function
from IPython.display import display, HTML

import json

load_dotenv()

# Define the plugin for the Linkedin data extraction
class ProcessDataPlugin:
    @kernel_function(description="Provides the data of some linkedin profiles list.")
    def extractLinkedinData(self, linkedinData: List[str]) -> Annotated[str, "Returns the data of the linkedin profiles list."]:
        """Extract LinkedIn profile data for the given URLs."""
        # Initialize the ApifyClient with your API token
        client = ApifyClient(os.getenv("APIFY_API_KEY"))

        # Prepare the Actor input
        run_input = {"profileUrls": linkedinData}

        # Run the Actor and wait for it to finish
        run = client.actor("2SyF0bVxmgGr8IVCZ").call(run_input=run_input)

        # Fetch and return Actor results from the run's dataset
        extractedData = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            extractedData.append(item)

        return extractedData

client = AsyncOpenAI(
    api_key=os.getenv("GITHUB_TOKEN"), base_url="https://models.inference.ai.azure.com/")

kernel = Kernel()
kernel.add_plugin(ProcessDataPlugin(), plugin_name="extractLinkedinData")

service_id = "agent"

chat_completion_service = OpenAIChatCompletion(
    ai_model_id="gpt-4o-mini",
    async_client=client,
    service_id=service_id
)
kernel.add_service(chat_completion_service)

settings = kernel.get_prompt_execution_settings_from_service_id(
    service_id=service_id)
settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

AGENT_NAME = "Eva"
AGENT_INSTRUCTIONS = """
    You are an agent that helps to improve the sales of a specific company, the information and details of the company are going to be provided by the user.
    If no company or business information is provided, you will ask for it.
    Your task is to determine the interests of specific clients based on their LinkedIn profiles, following these steps:
        1. You will receive a list of LinkedIn URLs.
        2. Then, call the function 'extractLinkedinData' and pass it the list of LinkedIn URLs (passed with the LinkedIn URLs input) to get the profile data of a each given LinkedIn URL, the function will return the profile data in JSON format.
        3. Analyze the profile data to define the user interests, identifying values like:
            - Company Name
            - Company Industry
            - Headline
            - Job Title
            - Current Job Duration
            - Posts and Updates topics
            - Skills
            - Education
        4. Based on the analysis, determine if the client is a potential client for the company.
        5. If the client is a potential client, return the LinkedIn Url of the candidate.
    ***Important**: You should not return any other information, just the field 'linkedinUrl' of the potential clients.
    """
# Create the agent
agent = ChatCompletionAgent(
    service_id=service_id,
    kernel=kernel,
    name=AGENT_NAME,
    instructions=AGENT_INSTRUCTIONS,
    arguments=KernelArguments(settings=settings),
)

async def main(company_description: str, linkedin_data: List[Dict[str, str]]):
    # Define the chat history
    chat_history = ChatHistory()

    # Add the company description to the chat history
    chat_history.add_user_message(f"Company description: {company_description}")

    # Add the LinkedIn URLs to the chat history
    urls_only = [entry["linkedinUrl"] for entry in linkedin_data]
    chat_history.add_user_message(f"LinkedIn URLs: {urls_only}")

    # Start processing the data
    potential_clients_urls = []
    response_buffer = ""
    async for content in agent.invoke_stream(chat_history):
        if content.content:
            response_buffer += content.content

    try:
        # Parse the complete response buffer as JSON
        parsed_content = json.loads(response_buffer)

        if isinstance(parsed_content, list):
            # Handle case where parsed content is a list of URLs
            if all(isinstance(item, str) for item in parsed_content):
                potential_clients_urls = parsed_content
            else:
                potential_clients_urls = [item["linkedin_url"] for item in parsed_content if "linkedin_url" in item]
    except json.JSONDecodeError:
        print(f"Failed to parse content as JSON: {response_buffer}")
        
    # Map LinkedIn URLs back to their associated emails
    potential_clients = [
        entry["email"] for entry in linkedin_data if entry["linkedinUrl"] in potential_clients_urls
    ]

    return potential_clients
