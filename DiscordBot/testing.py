from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load MongoDB credentials
load_dotenv("token.env")
PASSWORD = os.getenv('MONGO_PASSWORD')
PASSWORD = quote_plus(PASSWORD)  # Encode special chars

# Connect to MongoDB
uri = f"mongodb+srv://keatsliam:{PASSWORD}@aipicks.cdvhr.mongodb.net/?retryWrites=true&w=majority&appName=AiPicks"
client = MongoClient(uri, server_api=ServerApi('1'))


db = client["AI_Picks_Bot"]
nominations_collection = db["nominations"]
user_votes_collection = db["user_votes"]
ban_list_collection = db["ban_list"]

print("\n✅ Connected to database!")

while True:
    # Ask for User ID
    user_id = input("\nEnter a Discord user ID (or type 'done' to finish): ").strip()
    if user_id.lower() == "done":
        break  # Exit when finished
    if not user_id.isdigit():
        print("❌ Invalid user ID. Please enter numbers only.")
        continue

    user_id = int(user_id)  # Convert to integer

    # Ask for Player Name
    player_name = input("Nominate a player: ").strip()
    if player_name.lower() == "done":
        break  # Exit when finished

    player_name = player_name.title()  # Normalize case

    # Step 1: Ensure the user exists in `user_votes_collection`
    user_entry = user_votes_collection.find_one({"user_id": user_id})

    if not user_entry:
        user_votes_collection.insert_one({"user_id": user_id, "nominated_players": []})
        print(f"✅ Created new user entry for {user_id}.")

    # Step 2: Check if the user has already nominated 5 players
    user_entry = user_votes_collection.find_one({"user_id": user_id})
    if len(user_entry["nominated_players"]) >= 5:
        print("❌ User has reached the nomination limit (5).")
        continue

    # Step 3: Check if player already exists in nominations
    player_entry = nominations_collection.find_one({"player_name": player_name})

    if player_entry:
        nominations_collection.update_one(
            {"player_name": player_name},
            {"$inc": {"votes": 1}, "$addToSet": {"nominated_by": user_id}}
        )
        print(f"✅ {player_name} was nominated again. Votes updated.")
    else:
        nominations_collection.insert_one({
            "player_name": player_name,
            "nominated_by": [user_id],
            "votes": 1
        })
        print(f"✅ {player_name} was newly nominated.")

    # Step 4: Push the player's name to the user's nominations
    user_votes_collection.update_one(
        {"user_id": user_id},
        {"$push": {"nominated_players": player_name}}
    )
    print(f"✅ {player_name} added to user {user_id}'s nominations.\n")

# Print stored nominations
print("\n--- Nominations Collection ---")
for nomination in nominations_collection.find():
    print(nomination)

# Print stored user votes
print("\n--- User Votes Collection ---")
for user_vote in user_votes_collection.find():
    print(user_vote)

print("\n✅ Simulation complete! All nominations have been stored.")

nominations_collection.delete_many({})
user_votes_collection.delete_many({})
print("\n🗑️ All nominations have been cleared for the next round!")

print("\n✅ Simulation complete! All nominations have been stored.")
