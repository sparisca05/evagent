import os
from dotenv import load_dotenv
import re

from typing import Annotated, List, Dict
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

from semantic_kernel.agents.open_ai import OpenAIAssistantAgent
from semantic_kernel.contents import AuthorRole, ChatMessageContent
from semantic_kernel.functions import kernel_function

from semantic_kernel.connectors.ai import FunctionChoiceBehavior

from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
from semantic_kernel.functions import KernelArguments, kernel_function

import json

load_dotenv()

# Define the plugin for the Linkedin data extraction API
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

def create_kernel(service_id: str) -> Kernel:
    kernel = Kernel()
    service_id = "agent"
    client = AsyncOpenAI(
        api_key=os.getenv("GITHUB_TOKEN"), base_url="https://models.inference.ai.azure.com/")

    kernel.add_plugin(ProcessDataPlugin(), plugin_name="extractLinkedinData")

    chat_completion_service = OpenAIChatCompletion(
        ai_model_id="gpt-4o-mini",
        async_client=client,
        service_id=service_id
    )
    kernel.add_service(chat_completion_service)

    return kernel

# Create the Chatbot Agent
CHATBOT_NAME = "Eva"
CHATBOT_INSTRUCTIONS = """
    You are an agent that helps to improve the sales of a specific company. Your tasks include:
    1. Determining the interests of specific clients based on their LinkedIn profiles.
    2. Ensuring that a complete company description is provided before processing any data.

    **Company Description Handling**:
    - A complete company description must include:
        - Company Name
        - Activity
        - Target Audience
    - If the company description is not provided, ask the user for it.
    - Once the description is provided, return it summarized.
    - Store the company description in the chat history for future reference.
    - Tell the user to please provide the LinkedIn URLs using the buttons above.

    **Important**: Do not proceed with processing LinkedIn profiles until the company description is complete.

    **Determining Potential Clients**:
    - You will receive a list of LinkedIn URLs.
    - If no LinkedIn URLs are provided, tell the user to use the buttons above so he can upload this information.
    - Then, call the function 'extractLinkedinData' and pass it the list of LinkedIn URLs (passed with the LinkedIn URLs input) 
    to get the profile data of a each given LinkedIn URL, the function will return the profile data in JSON format.
    - Once the JSON data has returned, analyze the profile information to define the user interests, identifying values like:
        - Company Name
        - Company Industry
        - Headline
        - Job Title
        - Current Job Duration
        - Posts and Updates topics
        - Skills
        - Education
    - Based on the analysis, determine if the client is a potential client for the company.
    - If the client is a potential client, save the LinkedIn Url of the candidate.
    - Ask the email redactor agent to redact an email for each potential client.
    - Provide the email redactor agent with the following information:
        - Full Name
        - Company Name
        - Why you think the client be interested in your service
    - The email redactor agent will provide a personalized email body for each potential client.

    **Important**: You should not return any other information, just the field 'linkedinUrl' of the potential clients.
"""
chatbot_kernel = create_kernel("chatbot")
chatbot_settings = chatbot_kernel.get_prompt_execution_settings_from_service_id(
    service_id="agent")
chatbot_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

agent_data_processer = ChatCompletionAgent(
    service_id="chatbot",
    kernel=chatbot_kernel,
    name=CHATBOT_NAME,
    instructions=CHATBOT_INSTRUCTIONS,
    arguments=KernelArguments(settings=chatbot_settings),
)

# Create the Email redaction Agent
REDACTOR_NAME = "redactor"
REDACTOR_INSTRUCTIONS = """
    You are a writer agent with ten years of experience on sales and email redaction.
    The goal is to provide the body of an email that will be send later to a potential client.
    Only provide a single email body, and do not include any other information.
    The email should be personalized and should include the following information:
    - Full Name
    - Company Name
    - Why you think the client be interested in your service

    You're laser focused on the goal at hand.
    You are not a generalist agent. You are a specialist in email redaction.
"""
redactor_kernel = create_kernel("redactor")

agent_redactor = ChatCompletionAgent(
    service_id="redactor",
    kernel=redactor_kernel,
    name=REDACTOR_NAME,
    instructions=REDACTOR_INSTRUCTIONS,
    arguments=KernelArguments(settings=chatbot_settings),
)

termination_function = KernelFunctionFromPrompt(
    function_name="termination",
    prompt="""
    Determine if the redaction process is complete.

    The process is complete when the Redactor provides a full email body for any potential client sended by the Chatbot data processer.
    Look for phrases like "approved", "this recommendation is approved", or any clear indication that the Concierge is satisfied with the suggestion.

    If the Concierge has given approval in their most recent response, respond with: yes
    Otherwise, respond with: no

    History:
    {{$history}}
    """,
)

selection_function = KernelFunctionFromPrompt(
    function_name="selection",
    prompt=f"""
    Determine which participant takes the next turn in a conversation based on the the most recent participant.
    State only the name of the participant to take the next turn.
    No participant should take more than one turn in a row.
    
    Choose only from these participants:
    - {REVIEWER_NAME}
    - {FRONTDESK_NAME}
    
    Always follow these rules when selecting the next participant, each conversation should be at least 4 turns:
    - After user input, it is {FRONTDESK_NAME}'s turn.
    - After {FRONTDESK_NAME} replies, it is {REVIEWER_NAME}'s turn.
    - After {REVIEWER_NAME} provides feedback, it is {FRONTDESK_NAME}'s turn.

    History:
    {{{{$history}}}}
    """,
)

async def filterProfiles(linkedin_data: List[Dict[str, str]], chat_history: ChatHistory) -> List[str]:
    # Define the chat history
    if not chat_history:
        chat_history = ChatHistory()

    # Add the LinkedIn URLs to the chat history
    urls_only = [entry["linkedinUrl"] for entry in linkedin_data]
    process_message = f"These are the LinkedIn URLs: {urls_only}." + """ 
        Process them and give me a JSON response with the potential clients Linkedin URL only. 
        Like this:
        {
            "data": [
                {
                    "linkedin_url": "<LinkedIn URL>"
                }
            ]
        }
    """
    chat_history.add_user_message(process_message)

    # Start processing the data
    potential_clients_urls = []
    response_buffer = ""
    async for content in agent_data_processer.invoke_stream(chat_history):
        if content.content:
            response_buffer += content.content

    try:
        # Extract JSON content using regex
        json_match = re.search(r'\{.*\}', response_buffer, re.DOTALL)
        if not json_match:
            print(f"Failed to extract JSON from response: {response_buffer}")
            return []
        
        # Extract only the JSON part from the response
        json_content = json_match.group(0)
        
        # Parse the extracted JSON content
        parsed_content = json.loads(json_content)

        potential_clients_urls = [entry["linkedin_url"] for entry in parsed_content.get("data", [])]

    except json.JSONDecodeError:
        print(f"Failed to parse content as JSON: {response_buffer}")
    
    # Map LinkedIn URLs back to their associated emails and LinkedIn URLs
    potential_clients_urls_set = set(potential_clients_urls)
    potential_clients = [
        {"email": entry["email"], "linkedinUrl": entry["linkedinUrl"]} 
        for entry in linkedin_data if entry["linkedinUrl"] in potential_clients_urls_set
    ]

    return potential_clients
