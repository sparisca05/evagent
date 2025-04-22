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

project_client = AIProjectClient.from_connection_string(
    credential=InteractiveBrowserCredential(),
    conn_str=os.environ["PROJECT_CONNECTION_STRING"],
)

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

async def analyze_linkedin_profiles(company_description: str, linkedin_urls: List[str]) -> Dict[str, Any]:
    """
    Main function to run the LinkedIn profile analysis and email generation process.
    
    Args:
        company_description: Detailed description of the company
        linkedin_urls: List of LinkedIn profile URLs to analyze
    
    Returns:
        Dictionary containing analysis results and email drafts
    """
    # Add initial company description and LinkedIn URLs
    initial_message = f"""
    Company Description:
    {company_description}
    
    LinkedIn URLs to analyze:
    {json.dumps(linkedin_urls)}
    """
    await user_core_chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=initial_message))
    
    # Start the User-Core agent conversation
    response_buffer = ""
    async for message in user_core_chat.invoke(user_agent):
        if hasattr(message, "content") and message.content:
            response_buffer += message.content
    
    # Extract potential clients from Core agent response
    try:
        json_match = re.search(r'\{.*"potential_clients".*\}', response_buffer, re.DOTALL)
        if not json_match:
            return {"error": "Failed to extract potential clients from analysis"}
        
        analysis_result = json.loads(json_match.group(0))
        potential_clients = analysis_result.get("potential_clients", [])
        
        if not potential_clients:
            return {"message": "No potential clients found in the LinkedIn profiles.", "emails": []}
        
        # Prepare input for Email agent
        email_input = {
            "company_description": company_description,
            "potential_clients": potential_clients
        }
        
        # Create chat history for Email agent
        email_chat_history = ChatHistory()
        email_chat_history.add_user_message(json.dumps(email_input))
        
        # Invoke Email agent to draft emails
        email_response = ""
        async for content in email_agent.invoke_stream(email_chat_history):
            if hasattr(content, "content") and content.content:
                email_response += content.content
        
        # Extract email drafts
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

