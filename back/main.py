import json
import io
import re

from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from typing import List, Dict, Any
import pandas as pd
from pydantic import BaseModel

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from semantic_kernel.contents import ChatHistory

from azure_ai_agent import main as agent

app = FastAPI()

# Dictionary to store chat histories for each session
chat_histories = {}

# Store the connection string globally (in production, use a proper session management)
azure_connection_string = None

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessInviteesRequest(BaseModel):
    session_id: str
    linkedin_urls: List[str]

class ChatRequest(BaseModel):
    session_id: str
    message: str

class SendEmailsRequest(BaseModel):
    email_body: str
    potential_clients: List[str]

class ConnectionTestRequest(BaseModel):
    connection_string: str

class SetConnectionRequest(BaseModel):
    connection_string: str

class CompanyAnalysisRequest(BaseModel):
    company_description: str
    linkedin_urls: List[str]

class EmailGenerationRequest(BaseModel):
    company_description: str
    potential_clients: List[Dict[str, Any]]

@app.post("/test_connection/")
async def test_connection(request: ConnectionTestRequest):
    """Endpoint to test Azure connection string."""
    try:
        # Test the connection by attempting to create a client
        from azure.identity import DefaultAzureCredential
        from azure_ai_agent import create_kernel
        
        # Try to create a kernel with the provided connection string
        credential = DefaultAzureCredential()
        
        # Temporarily set the connection string for testing
        import os
        original_conn_str = os.environ.get("PROJECT_CONNECTION_STRING")
        os.environ["PROJECT_CONNECTION_STRING"] = request.connection_string
        
        try:
            # Try to create a simple kernel to test the connection
            kernel = create_kernel("test")
            
            # If we get here, the connection string is valid
            global azure_connection_string
            azure_connection_string = request.connection_string
            
            return {"status": "success", "message": "Connection successful"}
        except Exception as test_error:
            return JSONResponse(
                content={"status": "error", "message": f"Connection failed: {str(test_error)}"}, 
                status_code=400
            )
        finally:
            # Restore original connection string
            if original_conn_str:
                os.environ["PROJECT_CONNECTION_STRING"] = original_conn_str
            elif "PROJECT_CONNECTION_STRING" in os.environ:
                del os.environ["PROJECT_CONNECTION_STRING"]
                
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.post("/set_connection/")
async def set_connection(request: SetConnectionRequest):
    """Endpoint to set the Azure connection string for the session."""
    try:
        global azure_connection_string
        azure_connection_string = request.connection_string
        
        # Set it in environment for the current session
        import os
        os.environ["PROJECT_CONNECTION_STRING"] = request.connection_string
        
        return {"status": "success", "message": "Connection string set successfully"}
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/connection_status/")
async def get_connection_status():
    """Check if a connection string is currently set."""
    global azure_connection_string
    is_connected = azure_connection_string is not None
    
    return {
        "connected": is_connected,
        "message": "Connection established" if is_connected else "No connection established"
    }
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
    linkedin_urls: List[str]

@app.post("/process_invitees/")
async def process_invitees(request: ProcessInviteesRequest):
    """Endpoint to process LinkedIn profiles and determine potential clients."""
    try:
        # Retrieve or create a new chat history for the session
        if request.session_id not in chat_histories:
            chat_histories[request.session_id] = ChatHistory()

        chat_history: ChatHistory = chat_histories[request.session_id]
        message = f"LinkedIn urls: {request.linkedin_urls}"
        print(f"Processing LinkedIn URLs: {request.linkedin_urls}")
        
        # Check if connection string is available
        global azure_connection_string
        if not azure_connection_string:
            return JSONResponse(content={"error": "Azure connection not established. Please configure your connection first."}, status_code=400)
        
        response = await agent(message, chat_history, azure_connection_string)

        chat_history.add_user_message(message)
        chat_history.add_assistant_message(response)
        print(f"Agent response: {response}")
        # Parse the response to check if the description is provided
        try:
            # Extract JSON content using regex
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return JSONResponse(content={"error": "Failed to extract the json response"}, status_code=400)

            parsed_response = json.loads(json_match.group())
            print(f"Parsed response: {parsed_response}")
            retults = parsed_response.get("results", [])
            potential_clients = [client for client in retults if client.get("potential_match", False)]
        except json.JSONDecodeError:
            return JSONResponse(content={"error": "Failed to parse the response."}, status_code=400)
        
        return {"potential_clients": potential_clients}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/chat/")
async def chat(request: ChatRequest):
    """Endpoint to chat with the agent while maintaining memory."""
    try:
        # Retrieve or create a new chat history for the session
        if request.session_id not in chat_histories:
            chat_histories[request.session_id] = ChatHistory()

        chat_history: ChatHistory = chat_histories[request.session_id]

        # Check if connection string is available
        global azure_connection_string
        if not azure_connection_string:
            return JSONResponse(content={"error": "Azure connection not established. Please configure your connection first."}, status_code=400)

        response = await agent(request.message, chat_history, azure_connection_string)

        chat_history.add_user_message(request.message)
        chat_history.add_assistant_message(response)
        
        return {"response": response}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


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

                # Create the email content
                message = MIMEMultipart("alternative")
                message["Subject"] = "You're Invited to Our Event!"
                message["From"] = sender_email
                message["To"] = recipient_email

                message.attach(MIMEText(request.email_body, "plain"))

                # Send the email
                server.sendmail(sender_email, recipient_email, message.as_string())
            except Exception as e:
                return JSONResponse(content={"error": str(e)}, status_code=500)
            

        # Close the server connection
        server.quit()

        return {"message": "Emails sent successfully."}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/")
def read_root():
    return {"message": "LinkedIn Profile Analysis API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)