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
from semantic_kernel.contents import ChatHistory, ChatMessageContent, AuthorRole
from semantic_kernel.agents import ChatCompletionAgent, AgentGroupChat
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)

from semantic_kernel.functions import KernelFunctionFromPrompt
from semantic_kernel.connectors.ai import FunctionChoiceBehavior
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent
from semantic_kernel.functions import KernelArguments, kernel_function

load_dotenv()

# Define the plugin for the Linkedin data extraction API
class LinkedInDataPlugin:
    @kernel_function(name="extractLinkedinData", description="Provides the data of some LinkedIn profiles list.")
    def extractLinkedinData(self, linkedinUrls: List[str]) -> Annotated[str, "Returns the data of the linkedin profiles list."]:
        """Extract LinkedIn profile data for the given URLs."""
        # In production, use the Apify API call
        # client = ApifyClient(os.getenv("APIFY_API_KEY"))
        # run_input = {"profileUrls": linkedinUrls}
        # run = client.actor("2SyF0bVxmgGr8IVCZ").call(run_input=run_input)
        # extractedData = []
        # for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        #     extractedData.append({
        #         # Extract relevant profile data
        #     })
        
        # For testing, return sample data
        extractedData = [
            {
                "linkedinUrl": "https://www.linkedin.com/in/s4vitar/",
                "firstName": "Marcelo",
                "lastName": "Vázquez (Aka. S4vitar)",
                "headline": "Hack4u CEO & Founder / Pentester / YouTuber / Streamer",
                "jobTitle": "CEO & Founder",
                "companyName": "Hack4u",
                "companyIndustry": "E-Learning",
                "currentJobDuration": "2 yrs",
                "topSkillsByEndorsements": "Intrusión en sistemas, Encriptación, Bash, Seguridad, HackTheBox",
                "experiences": [
                    # Experience details omitted for brevity
                ],
                "skills": [
                    # Skills details omitted for brevity
                ]
            }
        ]

        return json.dumps(extractedData)

# Utility function to create kernels with specific settings
def create_kernel(service_id: str) -> Kernel:
    kernel = Kernel()
    client = AsyncOpenAI(
        api_key=os.getenv("GITHUB_TOKEN"), 
        base_url="https://models.inference.ai.azure.com/"
    )

    chat_completion_service = OpenAIChatCompletion(
        ai_model_id="gpt-4o-mini",
        async_client=client,
        service_id=service_id
    )
    kernel.add_service(chat_completion_service)

    return kernel

#
# Agent 1: User Interface Agent (Eva)
#
USER_AGENT_NAME = "Eva"
USER_AGENT_INSTRUCTIONS = """
You are Eva, a friendly assistant that helps users analyze LinkedIn profiles to find potential clients.

Your primary responsibilities are:
1. Ask the user for a detailed description of their company, products/services, and target audience.
2. Ensure the company description is detailed enough by asking clarifying questions if needed.
3. Once you have collected sufficient information, inform the user that you will analyze the LinkedIn profiles.
4. Pass the company description to the Core Agent for profile analysis.
5. If the Core Agent asks for more details about the company, relay those questions to the user and provide their responses back to the Core Agent.
6. When the Core Agent completes the analysis, share the results with the user.

Always be professional, concise, and helpful. Your goal is to gather enough information to help the Core Agent make accurate assessments.
"""

#
# Agent 2: LinkedIn Profile Analyzer Agent (Core)
#
CORE_AGENT_NAME = "LinkedInAnalyzer"
CORE_AGENT_INSTRUCTIONS = """
You are a LinkedIn profile analyzer specialized in identifying potential clients based on company descriptions.

Your responsibilities:
1. Receive company descriptions from the User Agent (Eva).
2. Evaluate if the company description is detailed enough to make accurate assessments:
   - If the description lacks necessary details, ask specific questions to gather more information.
   - Only proceed with profile analysis when you have sufficient information.
3. When the description is complete, analyze LinkedIn profiles by:
   - Calling the extractLinkedinData function with the provided LinkedIn URLs.
   - Evaluating each profile against the company description.
   - Determining which profiles represent potential clients based on factors like job role, industry, skills, etc.
4. Provide a clear report of potential clients with reasoning for your selections.
5. Format potential clients as a JSON object like:
   {
     "potential_clients": [
       {
         "linkedinUrl": "profile URL",
         "fullName": "First Last",
         "reason": "Brief explanation of match"
       }
     ],
     "analysis_complete": true
   }

Be thorough in your analysis and clear in your communication.
"""

#
# Agent 3: Email Drafting Agent (Redactor)
#
EMAIL_AGENT_NAME = "EmailDrafter"
EMAIL_AGENT_INSTRUCTIONS = """
You are an experienced email drafting specialist who creates personalized sales outreach emails.

Your responsibilities:
1. Receive information about potential clients and the company seeking to contact them.
2. Create personalized email bodies for each potential client that:
   - Address the recipient by name
   - Briefly introduce the company
   - Explain why your service/product is relevant to their specific needs (based on their profile)
   - Include a clear call-to-action
   - Maintain a professional yet friendly tone
3. Return your response as a JSON object with this format:
   {
     "emails": [
       {
         "linkedinUrl": "recipient's LinkedIn URL",
         "fullName": "First Last",
         "email_body": "Complete email body text"
       }
     ]
   }

Focus solely on creating effective email content. Do not provide additional commentary or explanations.
"""

# Create Kernels for each agent
user_agent_kernel = create_kernel("user_agent")
core_agent_kernel = create_kernel("core_agent")
email_agent_kernel = create_kernel("email_agent")

# Configure settings for agents that need special handling
core_agent_settings = core_agent_kernel.get_prompt_execution_settings_from_service_id("core_agent")
core_agent_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

# Create the agents
user_agent = ChatCompletionAgent(
    service_id="user_agent",
    kernel=user_agent_kernel,
    name=USER_AGENT_NAME,
    instructions=USER_AGENT_INSTRUCTIONS
)

core_agent = ChatCompletionAgent(
    service_id="core_agent",
    kernel=core_agent_kernel,
    name=CORE_AGENT_NAME,
    instructions=CORE_AGENT_INSTRUCTIONS,
    arguments=KernelArguments(settings=core_agent_settings)
)

email_agent = ChatCompletionAgent(
    service_id="email_agent",
    kernel=email_agent_kernel,
    name=EMAIL_AGENT_NAME,
    instructions=EMAIL_AGENT_INSTRUCTIONS
)

# Add the LinkedIn plugin to the core agent
core_agent.kernel.add_plugin(LinkedInDataPlugin(), plugin_name="LinkedIn")

# Define the selection function for agent group chat
selection_function = KernelFunctionFromPrompt(
    function_name="selection",
    prompt=f"""
        Determine which participant takes the next turn in a conversation based on the most recent message.
        State only the name of the participant to take the next turn.
        No participant should take more than one turn in a row unless necessary for clarification.

        The conversation is between the {USER_AGENT_NAME} agent and the {CORE_AGENT_NAME} agent.
            - The {USER_AGENT_NAME} agent collects company description from the user.
            - The {CORE_AGENT_NAME} agent analyzes the company description and LinkedIn profiles.
            - If the {CORE_AGENT_NAME} agent needs more information, it asks the {USER_AGENT_NAME} agent.
            - Once the {CORE_AGENT_NAME} agent has enough information, it will analyze the profiles and return results.

        Choose only from these participants:
        - {USER_AGENT_NAME}
        - {CORE_AGENT_NAME}

        History:
        {{{{$history}}}}
    """,
)

# Define the termination function for agent group chat
termination_function = KernelFunctionFromPrompt(
    function_name="termination",
    prompt="""
        Determine if the conversation between agents should terminate.
        
        Terminate the conversation if:
        1. The analysis has been completed, indicated by a message containing "analysis_complete": true
        2. The core agent has returned a final list of potential clients
        
        History:
        {{$history}}
    """
)

# Create the agent group chat for user interaction and profile analysis
user_core_chat = AgentGroupChat(
    agents=[user_agent, core_agent],
    termination_strategy=KernelFunctionTerminationStrategy(
        function=termination_function,
        kernel=create_kernel("termination"),
        result_parser=lambda result: "analysis_complete" in str(result.value[0]).lower(),
        history_variable_name="history",
        maximum_iterations=15,
    ),
    selection_strategy=KernelFunctionSelectionStrategy(
        function=selection_function,
        kernel=create_kernel("selection"),
        result_parser=lambda result: str(result.value[0]) if result.value else CORE_AGENT_NAME,
        history_variable_name="history",
    ),
)

async def analyze_linkedin_profiles(company_description: str, linkedin_urls: List[str]) -> Dict[str, Any]:
    """
    Main function to run the LinkedIn profile analysis and email generation process with interactive user feedback.
    
    Args:
        company_description: Initial description of the company
        linkedin_urls: List of LinkedIn profile URLs to analyze
    
    Returns:
        Dictionary containing analysis results and email drafts
    """
    # Create chat history as a list instead of ChatHistory object
    chat_history: List[ChatMessageContent] = []
    
    # Add initial company description and LinkedIn URLs
    initial_message = f"""
    Company Description:
    {company_description}
    
    LinkedIn URLs to analyze:
    {json.dumps(linkedin_urls)}
    """
    # Append a user message to chat_history instead of using add_user_message
    chat_history.append(ChatMessageContent(
        role=AuthorRole.USER,
        content=initial_message
    ))
    
    # Flag to track if analysis is complete
    analysis_complete = False
    potential_clients = []
    
    print("Starting conversation with the agent. Type your responses when prompted.")
    print("------------------------------------------------------")
    
    # Determine the next agent to speak based on conversation history
    await user_core_chat.add_chat_messages(chat_history)
    print("\n[User]: ", initial_message)

    # Interactive conversation loop
    while not analysis_complete:
        print("\n\n[Agent]: ", end="")
        # Get the agent's response
        response_buffer = ""
        async for content in user_core_chat.invoke():
            print("-")
            response_buffer += content.content
        print(response_buffer)
        print("Analysis completed: ", analysis_complete)
        # Check if the analysis is complete
        if "analysis_complete" in response_buffer.lower() or re.search(r'\{.*"potential_clients".*\}', response_buffer, re.DOTALL):
            try:
                json_match = re.search(r'\{.*"potential_clients".*\}', response_buffer, re.DOTALL)
                if json_match:
                    analysis_result = json.loads(json_match.group(0))
                    potential_clients = analysis_result.get("potential_clients", [])
                    if potential_clients:
                        analysis_complete = True
                        print("\n\nAnalysis complete!")
                        break
                    else:
                        # Handle case where analysis is complete but no potential clients were found
                        analysis_complete = True
                        print("\n\nAnalysis complete! No potential clients were found.")
                        break
            except json.JSONDecodeError:
                # Continue the conversation if JSON parsing fails
                pass
        
        # Add the agent response to chat history
        chat_history.append(ChatMessageContent(
            role=AuthorRole.ASSISTANT,
            content=response_buffer
        ))
        
        # If analysis not complete, get user input for follow-up
        if not analysis_complete:
            print("\n\n[Your response]: ", end="")
            user_input = input()
            chat_history.append(ChatMessageContent(
                role=AuthorRole.USER,
                content=user_input
            ))
        else:
            # Analysis is complete, break the loop
            break
    
    # Analysis is complete, proceed with email generation if potential clients were found
    if not potential_clients:
        return {"message": "No potential clients found in the LinkedIn profiles.", "emails": []}
    
    print("\nGenerating email drafts for potential clients...")
    
    # Prepare input for Email agent
    email_input = {
        "company_description": company_description,
        "potential_clients": potential_clients
    }
    
    # Create chat history for Email agent as a list
    email_chat_history: List[ChatMessageContent] = [
        ChatMessageContent(
            role=AuthorRole.USER,
            content=json.dumps(email_input)
        )
    ]
    
    # Invoke Email agent to draft emails
    email_response = ""
    print("\n[EmailDrafter]:")
    async for content in email_agent.invoke_stream(email_chat_history):
        if hasattr(content, "content") and content.content:
            print(content.content, end="", flush=True)
            email_response += content.content
    
    # Extract email drafts
    try:
        json_match = re.search(r'\{.*"emails".*\}', email_response, re.DOTALL)
        if not json_match:
            return {
                "potential_clients": potential_clients,
                "error": "Failed to generate email drafts"
            }
        
        email_results = json.loads(json_match.group(0))
        
        # Return combined results
        return {
            "potential_clients": potential_clients,
            "emails": email_results.get("emails", [])
        }
    
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse response as JSON: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

# Example usage
async def run_example():
    company_description = """
    We are TechSecure Solutions, a cybersecurity company specializing in penetration testing,
    vulnerability assessments, and security training for mid-size technology companies.
    Our target audience is tech firms that need to strengthen their security posture,
    particularly those working with sensitive customer data.
    """
    
    linkedin_urls = ["https://www.linkedin.com/in/s4vitar/"]
    
    result = await analyze_linkedin_profiles(company_description, linkedin_urls)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(run_example())
