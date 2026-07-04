# save as check_models.py
from google import genai

client = genai.Client(api_key="AQ.Ab8RN6KMaeJH8hL6kIhVk1QI1NPR6sTNbHO4M8rLSqkqDwoBbw")

print("Available models for your API key:\n")
for model in client.models.list():
    if 'generateContent' in model.supported_actions:
        print(f"  ✅ {model.name}")