# Evagent - AI-Powered LinkedIn Lead Generation Assistant

Evagent is an intelligent agent that helps businesses identify and connect with potential clients by analyzing LinkedIn profiles and automating personalized outreach. Built with Python, it leverages AI to streamline the lead generation process.

## Features

-   **AI-Powered Profile Analysis**: Analyzes LinkedIn profiles against your ideal customer criteria
-   **Smart Lead Qualification**: Automatically identifies the most promising potential clients
-   **Personalized Email Generation**: Creates customized outreach emails based on profile analysis
-   **Interactive Chat Interface**: Communicate with Eva, your AI assistant, for additional help
-   **Bulk Processing**: Handle multiple LinkedIn profiles simultaneously
-   **User-Friendly Interface**: Step-by-step guided process with clear instructions

## Tech Stack

### Frontend

-   React + TypeScript
-   Vite
-   Axios for API communication

### Backend

-   Python
-   FastAPI
-   Azure OpenAI for AI capabilities
-   Semantic Kernel for agent orchestration
-   Apify for LinkedIn data extraction

## Prerequisites

Before you begin, ensure you have the following installed:

-   Node.js (v19.0.0 or higher)
-   Python (3.11 or higher)
-   npm or yarn
-   pip

You'll also need:

-   An Azure Project Connection String
-   An Apify API key for LinkedIn data extraction

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/evagent.git
cd evagent
```

2. Set up the frontend:

```bash
cd front
npm install
```

3. Set up the backend:

```bash
cd back
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

4. Create a .env file in the backend directory with your API keys:

```env
AZURE_API_KEY=your_azure_api_key
APIFY_API_KEY=your_apify_api_key
PROJECT_CONNECTION_STRING=your_azure_connection_string
```

## Running the Application

1. Start the backend server:

```bash
cd back
python main.py
```

The backend will start on http://localhost:8000

2. Start the frontend development server:

```bash
cd front
npm run dev
```

The frontend will start on http://localhost:5173

## Usage Guide

1. **Company Profile Setup**

    - Enter your company name
    - Provide a detailed description of your business
    - Define your ideal customer profile
    - Use the sample data button to see an example

2. **Profile Upload**

    - Prepare an Excel file (.xlsx) containing LinkedIn profile URLs
    - Required columns: name, email, linkedin_url
    - Upload the file using drag-and-drop or file selector

3. **Profile Analysis**

    - The system will analyze each profile against your criteria
    - View real-time processing status
    - Review matched profiles and match reasons

4. **Email Generation**
    - Generate personalized emails for matched profiles
    - Review and customize generated emails
    - Send emails directly through the platform

## Features in Detail

### AI Profile Analysis

-   Evaluates professional background
-   Matches skills and experience
-   Considers industry alignment
-   Analyzes current role and responsibilities

### Smart Lead Qualification

-   Scores profiles based on match criteria
-   Provides detailed match reasoning
-   Filters out non-matching profiles
-   Prioritizes best matches

### Email Personalization

-   Creates context-aware email content
-   References specific profile details
-   Incorporates company value proposition
-   Maintains professional tone

## Troubleshooting

Common issues and solutions:

1. **API Connection Issues**

    - Verify your API keys in the .env file
    - Check your internet connection
    - Ensure Azure services are available

2. **File Upload Errors**

    - Verify Excel file format (.xlsx)
    - Check required column names
    - Ensure URLs are properly formatted

3. **Email Generation Issues**
    - Verify company information is complete
    - Check if profiles were successfully analyzed
    - Ensure all required data is present

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers directly.
