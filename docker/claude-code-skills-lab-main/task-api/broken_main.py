import os
import sys

print("Task API starting...")
print("Checking for required configuration...")

# Simulate missing required environment variable
api_key = os.environ.get("API_KEY")
if not api_key:
    print("ERROR: API_KEY environment variable is required but not set")
    sys.exit(1)

print(f"API_KEY configured: {api_key[:4]}****")
print("Starting server...")