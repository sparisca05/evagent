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
            extractedData.append({
                "linkedinUrl": item.get("linkedinUrl"),
                "firstName": item.get("firstName"),
                "lastName": item.get("lastName"),
                "headline": item.get("headline"),
                "companyName": item.get("companyName"),
                "companyIndustry": item.get("companyIndustry"),
                "jobTitle": item.get("jobTitle"),
                "currentJobDuration": item.get("currentJobDuration"),
                "education": item.get("education")
            })

        return extractedData

def create_kernel(service_id: str) -> Kernel:
    kernel = Kernel()
    service_id = "agent"
    client = AsyncOpenAI(
        api_key=os.getenv("GITHUB_TOKEN"), base_url="https://models.inference.ai.azure.com/")

    chat_completion_service = OpenAIChatCompletion(
        ai_model_id="gpt-4o-mini",
        async_client=client,
        service_id=service_id
    )
    kernel.add_service(chat_completion_service)

    return kernel

# Create the description agent
DESCRIPTION_NAME = "Eva"
DESCRIPTION_INSTRUCTIONS = """
    You are an assistant that collects a company description from the user.
    Your tasks include:
    1. Asking the user for a complete company description.
    2. Ensuring that the description includes:
        - Company Name
        - Activity
        - Target Audience
    3. If the description is not provided, ask the user for it.
    4. Once the description is provided, return it summarized and state that it is completed in a new message.
    """
description_kernel = create_kernel("Eva")
agent_description = ChatCompletionAgent(
    service_id="Eva",
    kernel=description_kernel,
    name=DESCRIPTION_NAME,
    instructions=DESCRIPTION_INSTRUCTIONS,
)

# Create the Core Agent
CORE_NAME = "core"
CORE_INSTRUCTIONS = """
    You are an agent that helps to improve the sales of a specific company.
    The goal is to determine the interests of specific clients based on their LinkedIn profiles.

    - You will receive a list of LinkedIn URLs.
    - Then, call the function 'extractLinkedinData' and pass it the list of LinkedIn URLs provided before
    to get the profile data of a each given LinkedIn URL, the function will return the profile data in JSON format.
    **Only do one call to the function 'extractLinkedinData' per LinkedIn URL.**
    - Once the JSON data has returned, analyze the profile information to define if the user is a potential client based on the interests, identifying values like:
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
    - Finally, ask the email redactor agent to redact an email for each potential client.
"""
chatbot_kernel = create_kernel("core")
chatbot_settings = chatbot_kernel.get_prompt_execution_settings_from_service_id(
    service_id="agent")
chatbot_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

agent_data_processer = ChatCompletionAgent(
    service_id="core",
    kernel=chatbot_kernel,
    name=CORE_NAME,
    instructions=CORE_INSTRUCTIONS,
    arguments=KernelArguments(settings=chatbot_settings),
)

agent_data_processer.kernel.add_plugin(
    ProcessDataPlugin(), plugin_name="extractLinkedinData"
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

    This information will be provided by the Chatbot agent.
    If the information is not provided or is incomplete, ask the Chatbot agent for it.
    The email should be written in a professional and friendly tone.
    You're laser focused on the goal at hand.
    You are not a generalist agent. You are a specialist in email redaction.

    **Important**: You should not return any other information, just the email body.
    The email body should be in the following format:
    {
        "email_body": "<Email Body>"
    }
"""
redactor_kernel = create_kernel("redactor")

agent_redactor = ChatCompletionAgent(
    service_id="redactor",
    kernel=redactor_kernel,
    name=REDACTOR_NAME,
    instructions=REDACTOR_INSTRUCTIONS,
)

termination_function = KernelFunctionFromPrompt(
    function_name="termination",
    prompt="""
        Determine if the redaction process is complete.

        The process is complete when the redactor provides a full email body of any potential client sended by the core agent.
        The email body should be in the following format:
        {
            "email_body": "<Email Body>"
        }

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
        
        There would be three different conversation escenarios:
        1. The first one is between the user and the {DESCRIPTION_NAME} agent, who will later respond to {CORE_NAME}.
            - The {DESCRIPTION_NAME} agent will ask the user for a complete company description and the LinkedIn URLs.
            - The user will provide the company description and the LinkedIn URLs.
            - Finally, the {DESCRIPTION_NAME} agent will provide the {CORE_NAME} agent (exclusively only to {CORE_NAME}) a summarized company description and 
            LikedIn URLs list and a message containing the word 'completed', seek for that term to pass to the next conversation.
        
        2. The second conversation is between the {DESCRIPTION_NAME} agent and the {CORE_NAME} agent.
            - The {DESCRIPTION_NAME} agent will provide the {CORE_NAME} agent a summarized company description and LikedIn URLs list.
            - The {CORE_NAME} agent will process the LinkedIn URLs and determine the potential clients.
            - The {CORE_NAME} agent will ask the {REDACTOR_NAME} agent to redact an email for each potential client.
            - The {CORE_NAME} agent will provide the {REDACTOR_NAME} agent with the following information:
                - Full Name
                - Company Name
                - Why you think the client be interested in your service

        3. The third one is between the {CORE_NAME} agent and the {REDACTOR_NAME} agent.
            - The {REDACTOR_NAME} agent will provide a personalized email body for each potential client.

        Choose only from these participants:
        - {DESCRIPTION_NAME}
        - {CORE_NAME}
        - {REDACTOR_NAME}

        History:
        {{{{$history}}}}
    """,
)

chat = AgentGroupChat(
    agents=[agent_description, agent_data_processer, agent_redactor],
    termination_strategy=KernelFunctionTerminationStrategy(
        agents=[agent_redactor],
        function=termination_function,
        kernel=create_kernel("termination"),
        result_parser=lambda result: "email_body" in str(result.value[0]).lower(),
        history_variable_name="history",
        maximum_iterations=10,
    ),
    selection_strategy=KernelFunctionSelectionStrategy(
        function=selection_function,
        kernel=create_kernel("selection"),
        result_parser=lambda result: str(
            result.value[0]) if result.value is not None else CORE_NAME,
        agent_variable_name="agents",
        history_variable_name="history",
    ),
)

# Function to filter LinkedIn profiles
async def filterProfiles(linkedin_data: List[Dict[str, str]], chat_history: ChatHistory) -> List[str]:
    # Define the chat history if not provided
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
