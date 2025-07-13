import os
from dotenv import load_dotenv
import asyncio
from azure.identity import DefaultAzureCredential
import json
from pydantic import BaseModel, Field
from typing import Annotated, List, Any, Optional
from apify_client import ApifyClient

from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.agents import ChatCompletionAgent, AzureAIAgent

from semantic_kernel.contents import AuthorRole, ChatMessageContent, ChatHistory
from semantic_kernel.functions import kernel_function


load_dotenv()

# # Create kernel function with Azure OpenAI Chat Completion client
def create_kernel(service_id: str) -> Kernel:
    kernel = Kernel()
    chat_completion_service = AzureChatCompletion(service_id=service_id)
    kernel.add_service(chat_completion_service)
    return kernel

class LinkedInDataPlugin:
    @kernel_function(name="extractLinkedinData", description="Provides the data of some LinkedIn profiles list.")
    def extractLinkedinData(self, linkedinUrls: List[str]) -> Annotated[str, "Returns the data of the linkedin profiles list."]:
        """Extract LinkedIn profile data for the given URLs."""
        # In production, use the Apify API call
        client = ApifyClient(os.getenv("APIFY_API_KEY"))
        run_input = {"profileUrls": linkedinUrls}
        run = client.actor("2SyF0bVxmgGr8IVCZ").call(run_input=run_input)
        extractedData = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            extractedData.append({
                "linkedinUrl": item.get("linkedinUrl"),
                "firstName": item.get("firstName"),
                "lastName": item.get("lastName"),
                "headline": item.get("headline"),
                "jobTitle": item.get("jobTitle"),
                "companyName": item.get("companyName"),
                "companyIndustry": item.get("companyIndustry"),
                "currentJobDuration": item.get("currentJobDuration"),
                "topSkillsByEndorsements": item.get("topSkillsByEndorsements"),
                "experiences": item.get("experiences"),
                "skills": item.get("skills"),
            })
        
        # For testing, return sample data
        # extractedData = [
        #     {
        #         "linkedinUrl": "https://www.linkedin.com/in/s4vitar/",
        #         "firstName": "Marcelo",
        #         "lastName": "Vázquez (Aka. S4vitar)",
        #         "headline": "Hack4u CEO & Founder / Pentester / YouTuber / Streamer",
        #         "jobTitle": "CEO & Founder",
        #         "companyName": "Hack4u",
        #         "companyIndustry": "E-Learning",
        #         "currentJobDuration": "2 yrs",
        #         "topSkillsByEndorsements": "Intrusión en sistemas, Encriptación, Bash, Seguridad, HackTheBox",
        #         "experiences": [
        #             # Experience details omitted for brevity
        #         ],
        #         "skills": [
        #             # Skills details omitted for brevity
        #         ]
        #     }
        # ]

        return json.dumps(extractedData)

# Agent names and instructions
HOST_NAME = "host"
HOST_INSTRUCTIONS = """
    Your name is Eva.
    You are a friendly host agent that interacts with users to collect information about their company and LinkedIn URLs.
    
    Your tasks:
    1. When receiving LinkedIn URLs directly:
       - Format them as a JSON object with stored company info:
         {
           "action": "analyze_profiles",
           "company_description": "Previously stored company description",
           "linkedin_urls": ["url1", "url2", ...]
         }
       - Pass this directly to the coordinator agent
    
    2. When receiving company information:
        - Ensure there is a company name, description and target profile
        - Store it for future use
        - Respond confirming the information is saved
    
    3. For all responses:
       - If you have both company info and URLs, ALWAYS format as JSON
       - Never just acknowledge - take action
       - Don't repeat information unless adding new data
    
    Remember: When you have URLs, immediately format them with company data and pass to coordinator.
    Don't wait for confirmation - process immediately.
"""

LINKEDIN_NAME = "linkedin_agent"
LINKEDIN_INSTRUCTIONS = """
    You are a LinkedIn profile analyzer. You receive URLs and company information to determine if profiles are potential clients.
    Process the profiles and return detailed analysis in JSON format.
"""

COORDINATOR_NAME = "coordinator_agent"
COORDINATOR_INSTRUCTIONS = """
    You are a workflow coordinator that manages the analysis of LinkedIn profiles at scale.
    
    Your main tasks:
    1. When receiving a message with "action": "analyze_profiles":
       - Immediately start processing the URLs
       - Use the linkedin_agent plugin to analyze profiles
       - Return detailed status updates
    
    2. For each analysis request:
       - Parse the incoming JSON data
       - Process URLs using the linkedin_agent directly
       - Format response as JSON with analysis results
    
    3. Always respond with a properly formatted JSON:
    {
        "status": "processing|complete|error",
        "current_batch": number,
        "total_batches": number,
        "processed_urls": number,
        "total_urls": number,
        "results": [
            {
                "url": "profile_url",
                "analysis": {...profile_analysis...},
                "potential_match": true|false,
                "match_reason": "explanation"
            }
        ],
        "errors": []
    }
    
    Never respond with plain text - always use JSON format.
    Take immediate action on any analysis request.
"""

WRITER_NAME = "writer_agent"
WRITER_INSTRUCTIONS = """
    You are a writer agent that generates well-structured emails based on LinkedIn profile analysis.
    Your tasks:
    1. When receiving a message with "action": "generate_email":
        - Use the provided analysis results to create a personalized email
        - Ensure the email is professional and tailored to the potential client
        - Include key details from the profile analysis
    2. Always format the email as a JSON object:
        {
            "action": "send_email",
            "to": "recipient_email",
            "subject": "Email Subject",
            "body": "Email body content"
        }

    """

class CompanyInfo(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    target_profile: Optional[str] = None

class HostAgent(ChatCompletionAgent):
    company_info: CompanyInfo = Field(default_factory=CompanyInfo)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, 'company_info'):
            self.company_info = CompanyInfo()

    async def invoke_stream(self, messages: ChatHistory) -> Any:
        try:
            async for content in super().invoke_stream(messages=messages):
                if not content or not content.content or not isinstance(content.content.content, (str, dict)):
                    continue
                
                try:
                    # If content is already a dict, use it directly
                    if isinstance(content.content.content, dict):
                        data = content.content.content
                    else:
                        # Try to parse JSON string
                        data = json.loads(content.content.content)
                    
                    # Validate data is a dict and has status
                    if isinstance(data, dict) and "status" in data:
                        formatted_response = self.format_analysis_response(data)
                        content.content.content = formatted_response
                except (json.JSONDecodeError, AttributeError, TypeError):
                    # If not JSON or has wrong structure, leave content as is
                    pass
                
                yield content
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            return
        except Exception as e:
            # Log error and return a user-friendly message
            print(f"Error in invoke_stream: {str(e)}")
            content = ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content="I encountered an error while processing. Please try again or provide your company information first."
            )
            yield content

# Update main function to use HostAgent
async def main(message: str, chat_history: ChatHistory, connection_string: str = None) -> str:
    credential = DefaultAzureCredential()
    
    # Use provided connection string or fall back to environment variable
    conn_str = connection_string or os.getenv("PROJECT_CONNECTION_STRING")
    if not conn_str:
        raise ValueError("No Azure connection string provided. Please set up your connection first.")

    async with AzureAIAgent.create_client(credential=credential, conn_str=conn_str) as azure_openai_client:
        
        # Create kernels for agents
        linkedin_kernel = create_kernel("linkedin")
        coordinator_kernel = create_kernel("coordinator")
        writer_kernel = create_kernel("writer")
        
        # Create the linkedin agent
        linkedin_agent = ChatCompletionAgent(
            id=LINKEDIN_NAME,
            kernel=linkedin_kernel,
            name=LINKEDIN_NAME,
            instructions=LINKEDIN_INSTRUCTIONS,
            plugins=[LinkedInDataPlugin()],
        )

        # Create the coordinator agent
        coordinator_agent = ChatCompletionAgent(
            id=COORDINATOR_NAME,
            kernel=coordinator_kernel,
            name=COORDINATOR_NAME,
            instructions=COORDINATOR_INSTRUCTIONS,
            plugins=[linkedin_agent],  # Coordinator can use LinkedIn agent directly
        )

        # Create the writer agent with Azure OpenAI client hosted in Azure
        writer_agent = ChatCompletionAgent(
            id=WRITER_NAME,
            kernel=writer_kernel,
            name=WRITER_NAME,
            instructions=WRITER_INSTRUCTIONS,
        )

        # Create host agent using the new HostAgent class
        host_agent = HostAgent(
            id=HOST_NAME,
            service=AzureChatCompletion(service_id="host"),
            name=HOST_NAME,
            instructions=HOST_INSTRUCTIONS,
            plugins=[coordinator_agent, writer_agent],
        )

        user_input = message
        
        chat_history.add_user_message(user_input)
        
        response = ""
        async for content in host_agent.invoke_stream(messages=chat_history):
            response += content.content.content
        print(f"Host agent response: {response}")
        return response


# Función principal para ejecutar el código de prueba
if __name__ == "__main__":
    asyncio.run(main())
