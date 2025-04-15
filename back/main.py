import os
from dotenv import load_dotenv

import random
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
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

import pandas as pd
from pydantic import BaseModel

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from agent import main as agent_main

app = FastAPI()
load_dotenv()

# Store company description and LinkedIn URLs globally for simplicity
company_description = {}
linkedin_urls = []

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define a model for the company description
class CompanyDescription(BaseModel):
    name: str
    activity: str
    target_audience: str

@app.post("/upload_excel/")
async def upload_excel(file: UploadFile):
    """Endpoint to upload the Excel file with invitees."""
    try:
        # Read the Excel file
        df = pd.read_excel(file.file)
        if not all(col in df.columns for col in ["name", "email", "linkedin_url"]):
            return JSONResponse(content={"error": "The file must contain 'name', 'email', and 'linkedin_url' columns."}, status_code=400)

        # Extract LinkedIn URLs and associated emails
        global linkedin_data
        linkedin_data = [
            {"linkedinUrl": row["linkedin_url"], "email": row["email"]}
            for _, row in df.iterrows()
        ]
        return {"message": "Excel file processed successfully.", "linkedin_data": linkedin_data}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/set_company_description/")
async def set_company_description(description: CompanyDescription):
    """Endpoint to set the company description."""
    global company_description
    company_description = description
    return {"message": "Company description set successfully.", "company_description": company_description}

@app.post("/process_invitees/")
async def process_invitees():
    """Endpoint to process LinkedIn profiles and determine potential clients."""
    try:
        if not company_description or not linkedin_data:
            return JSONResponse(content={"error": "Company description or LinkedIn URLs are missing."}, status_code=400)

        # Use the agent to analyze LinkedIn profiles
        global potential_clients_emails
        potential_clients = await agent_main(company_description, linkedin_data)
        potential_clients_emails = potential_clients
        return potential_clients
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
@app.post("/send_emails/")
async def send_emails(potential_clients: List[str]):
    """Endpoint to send personalized emails to potential clients."""
    try:
        # Email server configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "simonpariscam@gmail.com"
        sender_password = "mrqt jajo flix jcej"

        # Connect to the email server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send emails to potential clients
        for client in potential_clients:
            recipient_email = client
            if not recipient_email:
                continue

            # Create the email content
            message = MIMEMultipart("alternative")
            message["Subject"] = "You're Invited to Our Event!"
            message["From"] = sender_email
            message["To"] = recipient_email

            # Customize the email body
            email_body = f"""
            Hi,

            We are excited to invite you to our upcoming event! This is a great opportunity to connect and learn more about our company.

            Looking forward to seeing you there!

            Best regards,
            The Team
            """

            message.attach(MIMEText(email_body, "plain"))

            # Send the email
            server.sendmail(sender_email, recipient_email, message.as_string())

        # Close the server connection
        server.quit()

        return {"message": "Emails sent successfully."}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
