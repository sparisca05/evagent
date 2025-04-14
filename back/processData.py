from apify_client import ApifyClient
from dotenv import load_dotenv
import os

def extractLinkedinData(linkedinUrls):
    load_dotenv()

    # Initialize the ApifyClient with your API token
    client = ApifyClient(os.getenv("APIFY-API-KEY"))
    extractedData = []

    # Prepare the Actor input
    run_input = { "profileUrls": linkedinUrls }

    # Run the Actor and wait for it to finish
    run = client.actor("2SyF0bVxmgGr8IVCZ").call(run_input=run_input)

    # Fetch and print Actor results from the run's dataset (if there are any)
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        extractedData.append(item)

    return extractedData