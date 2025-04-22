import json
import io
import re
from uuid import uuid4

from fastapi import FastAPI, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from typing import List, Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from agent import filterProfiles, agent_data_processer, analyze_linkedin_profiles
from semantic_kernel.contents import ChatHistory

app = FastAPI()

# Dictionary to store chat histories for each session
chat_histories = {}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload_excel/")
async def upload_excel(file: UploadFile):
    """Endpoint to upload the Excel file with invitees."""
    try:
        # Convert the uploaded file to a BytesIO object
        contents = await file.read()
        excel_data = io.BytesIO(contents)

        # Read the Excel file
        df = pd.read_excel(excel_data)
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

class ProcessInviteesRequest(BaseModel):
    session_id: str

@app.post("/process_invitees/")
async def process_invitees(request: ProcessInviteesRequest):
    """Endpoint to process LinkedIn profiles and determine potential clients."""
    try:
        global company_description  # Mark company_description as global

        # Check if the session ID is valid
        if request.session_id not in chat_histories:
            chat_histories[request.session_id] = ChatHistory()

        chat_history = chat_histories[request.session_id]

        user_message = """Do we have a complete company description? If we have it, please provide it in this JSON format:
            {
                "name": "<Company Name>",
                "activity": "<Activity>",
                "target_audience": "<Target Audience>"
            }
        """
        chat_history.add_user_message(user_message)

        response_buffer = ""
        async for content in agent_data_processer.invoke_stream(chat_history):
            if content.content:
                response_buffer += content.content

        # Parse the response to check if the description is provided
        try:
            # Extract JSON content using regex
            json_match = re.search(r'\{.*\}', response_buffer, re.DOTALL)
            if not json_match:
                return JSONResponse(content={"error": "Failed to extract the company description. Please provide it via the chat."}, status_code=400)

            parsed_response = json.loads(json_match.group())

            if all(key in parsed_response for key in ["name", "activity", "target_audience"]):
                company_description = parsed_response
            else:
                return JSONResponse(content={"error": "Company description is incomplete. Please provide it via the chat."}, status_code=400)
        except json.JSONDecodeError:
            return JSONResponse(content={"error": "Failed to parse the company description. Please provide it via the chat."}, status_code=400)

        # Proceed with processing LinkedIn profiles
        if not linkedin_data:
            return JSONResponse(content={"error": "LinkedIn URLs are missing."}, status_code=400)

        potential_clients = await filterProfiles(linkedin_data, chat_history)
        return {"filtered_data": potential_clients}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat/")
async def chat(request: ChatRequest):
    """Endpoint to chat with the agent while maintaining memory."""
    try:
        # Retrieve or create a new chat history for the session
        if request.session_id not in chat_histories:
            chat_histories[request.session_id] = ChatHistory()

        chat_history = chat_histories[request.session_id]

        # Add the user's message to the chat history
        chat_history.add_user_message(request.message)

        # Get the agent's response
        response_buffer = ""
        async for content in agent_data_processer.invoke_stream(chat_history):
            if content.content:
                response_buffer += content.content

        # Add the agent's response to the chat history
        chat_history.add_assistant_message(response_buffer)

        return {"response": response_buffer}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

class SendEmailsRequest(BaseModel):
    session_id: str
    potential_clients: List[str]
@app.post("/send_emails/")
async def send_emails(request: SendEmailsRequest):
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
        for client in request.potential_clients:
            recipient_email = client
            if not recipient_email:
                continue
            # Ask the agent for the email content
            try:
                # Retrieve or create a new chat history for the session
                if request.session_id not in chat_histories:
                    return JSONResponse(content={"error": "Session ID not found."}, status_code=400)

                chat_history = chat_histories[request.session_id]

                # Add the user's message to the chat history
                input_message = f"Please write a personalized email to {recipient_email}."
                chat_history.add_user_message(input_message)

                # Get the agent's response
                response_buffer = ""
                async for content in agent.invoke_stream(chat_history):
                    if content.content:
                        response_buffer += content.content

                # Add the agent's response to the chat history
                chat_history.add_assistant_message(response_buffer)

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
            except Exception as e:
                return JSONResponse(content={"error": str(e)}, status_code=500)
            

        # Close the server connection
        server.quit()

        return {"message": "Emails sent successfully."}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

class CompanyAnalysisRequest(BaseModel):
    company_description: str
    linkedin_urls: List[str]

class EmailGenerationRequest(BaseModel):
    company_description: str
    potential_clients: List[Dict[str, Any]]

@app.get("/")
def read_root():
    return {"message": "LinkedIn Profile Analysis API"}

@app.post("/analyze")
async def analyze_profiles(request: CompanyAnalysisRequest):
    """
    Analyze LinkedIn profiles based on company description
    and generate personalized email drafts for potential clients
    """
    try:
        # Call the multi-agent system to analyze profiles and generate emails
        result = await analyze_linkedin_profiles(
            company_description=request.company_description,
            linkedin_urls=request.linkedin_urls
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)