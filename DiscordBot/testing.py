import difflib
from cogs.other.player_names import * 

# # List of NBA players (example)
# nba_players = player_names

# test_names = [
#     "Nikola Jovic", "Zaccharie Risache", "Nigga James", "Lavar Ball",
#     "Ai Picks", "Jamal Murray", "Jordon Poole", "Anyone In The Nba",
#     "Any Bench Bum", "Kat", "Tyrease Haliburton"
# ]

# for name in test_names:
#     matches = difflib.get_close_matches(name, nba_players, n=3, cutoff=0.6)
    
#     if matches:  # If we have at least one match
#         response = f"User input: {name} -> Closest matches: {matches}"
#     else:
#         response = f"User input: {name} -> No close matches found. Please check spelling!"
    
#     print(response)  # Replace with bot.send_message() if needed



from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv("token.env")
PASSWORD = os.getenv('MONGO_PASSWORD')
PASSWORD = quote_plus(PASSWORD)  # Encode special chars

uri = f"mongodb+srv://keatsliam:{PASSWORD}@aipicks.cdvhr.mongodb.net/?retryWrites=true&w=majority&appName=AiPicks"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)