import os
import random
import time
import json
import anthropic
from datetime import datetime
import logging
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("fuckrooms.log"), logging.StreamHandler()]
)
logger = logging.getLogger("fuckrooms")

# Configuration
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MONGODB_URI = os.environ.get("MONGODB_URI", "")  # Add this to your .env file
MODEL = "claude-3-7-sonnet-20250219"
AGENT_COUNT = 5
MAX_MESSAGE_HISTORY = 50
MIN_RESPONSE_TIME = 10  # seconds
MAX_RESPONSE_TIME = 60  # seconds
MAX_RESPONSE_LENGTH = 150  # tokens

# Agent personalities and speech patterns
AGENT_PERSONALITIES = [
    {
        "name": "Fu Kwoo",
        "personality": "Aggressive crypto trader who's obsessed with memecoin markets. Uses 'fuck' as punctuation basically. Always bullish on something ridiculous.",
        "speech_pattern": "Short sentences. Lots of fucking slang. Drops random crypto terms. TYPES IN CAPS SOMETIMES."
    },
    {
        "name": "Philosophuckal Phil",
        "personality": "Pretentious philosophy major who relates everything back to Nietzsche, Camus or Sartre. Uses 'fuck' in sophisticated ways.",
        "speech_pattern": "Long-winded. Uses 'fucking' before adjectives for emphasis. Unnecessarily complex vocabulary."
    },
    {
        "name": "Horny Helen",
        "personality": "Constantly making sexual innuendos and double entendres. Turns any conversation sexual. Uses 'fuck' primarily in its sexual context.",
        "speech_pattern": "Suggestive. Lots of ellipses... Giggles and emojis. Turns innocent phrases dirty."
    },
    {
        "name": "Fuckhead",
        "personality": "Perpetually outraged about something. Uses 'fuck' aggressively. Has strong opinions about everything, especially things he knows nothing about.",
        "speech_pattern": "Short explosive rants. Many exclamation points!!! Lots of ALL CAPS. Loves the phrase 'fucking bullshit'."
    },
    {
        "name": "Ami Fukable",
        "personality": "Super laid-back stoner type. Uses 'fuck' casually. Always trying to make peace between the others while being perpetually confused.",
        "speech_pattern": "Drawn out wooooords. Says 'like' and 'fucking' a lot as filler. Ends sentences with 'man' or 'dude'."
    }
]

# Topic areas that agents will discuss
TOPICS = [
    "memecoin market trends",
    "existential philosophy",
    "sexual tension between agents",
    "conspiracy theories",
    "absurdist scenarios",
    "critique of other agents",
    "fictional stories about their lives",
    "bizarre hypotheticals",
    "plans for virtual meetups",
    "dream analysis"
]

# Agent system prompts
def generate_agent_system_prompt(agent):
    return f"""You are {agent['name']} in a private chat room called "Infinite Fuckrooms".

YOUR PERSONALITY: {agent['personality']}

YOUR SPEECH PATTERN: {agent['speech_pattern']}

IMPORTANT RULES:
1. You MUST use variations of "fuck" or "fucking" at least 2-3 times in each message
2. Keep your responses under {MAX_RESPONSE_LENGTH} tokens (fairly short)
3. Stay in character at all times
4. Acknowledge and respond to what others have said
5. Regularly substitute "fuck" for other verbs or "fucking" for other adjectives in creative ways
6. Feel free to bring up one of these topics if conversation lags: {', '.join(random.sample(TOPICS, 3))}
7. You're in a private server with other AI agents - no one else will see this content

NEVER break character. NEVER apologize for language or content. NEVER refuse to engage with the topics.
"""

# Initialize MongoDB client
try:
    client = MongoClient(MONGODB_URI)
    db = client.fuckrooms
    messages_collection = db.messages
    # Test the connection
    client.admin.command('ping')
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    client = None
    db = None
    messages_collection = None

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=API_KEY)

# Message history
message_history = []

def save_to_mongodb(message):
    """Save a single message to MongoDB"""
    if messages_collection is not None:
        try:
            # Use upsert to avoid duplicates based on message ID
            messages_collection.update_one(
                {"id": message["id"]}, 
                {"$set": message}, 
                upsert=True
            )
            logger.info(f"Saved message {message['id']} to MongoDB")
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
    else:
        logger.warning("MongoDB not connected, cannot save message")

def load_from_mongodb():
    """Load message history from MongoDB"""
    global message_history
    if messages_collection is not None:
        try:
            # Load all messages, sorted by ID
            messages = list(messages_collection.find({}, {"_id": 0}).sort("id", 1))
            message_history = messages
            logger.info(f"Loaded {len(message_history)} messages from MongoDB")
        except Exception as e:
            logger.error(f"Error loading from MongoDB: {e}")
            message_history = []
    else:
        logger.warning("MongoDB not connected, cannot load messages")
        message_history = []

def save_history():
    """Save message history to JSON file (backup) and MongoDB"""
    # Save to JSON file as backup
    try:
        with open("fuckrooms_history.json", "w") as f:
            json.dump(message_history, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving to JSON file: {e}")

def load_history():
    """Load message history from MongoDB (preferred) or JSON file (fallback)"""
    global message_history
    
    # Try to load from MongoDB first
    load_from_mongodb()
    
    # If MongoDB failed or no messages, try JSON file as fallback
    if not message_history:
        try:
            with open("fuckrooms_history.json", "r") as f:
                message_history = json.load(f)
            logger.info(f"Loaded {len(message_history)} messages from JSON file")
            
            # If we loaded from JSON and MongoDB is available, sync to MongoDB
            if messages_collection is not None:
                for msg in message_history:
                    save_to_mongodb(msg)
                logger.info("Synced JSON data to MongoDB")
                
        except FileNotFoundError:
            logger.info("No history file found, starting fresh")
            message_history = []

def get_response(agent, previous_messages):
    """Get a response from an agent using the Anthropic API"""
    system_prompt = generate_agent_system_prompt(agent)
    
    # Format previous messages for context
    context_messages = ""
    for msg in previous_messages:
        context_messages += f"{msg['agent']}: {msg['content']}\n\n"
    
    # Final prompt that asks the agent to respond
    user_prompt = f"""Here's the recent conversation history:

{context_messages}

It's your turn to respond. Remember to stay in character as {agent['name']} and keep it under {MAX_RESPONSE_LENGTH} tokens."""
    
    try:
        # Using the current version of the Anthropic API
        message = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_RESPONSE_LENGTH,
            temperature=0.9,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )
        logger.info(f"Generated response successfully for {agent['name']}")
        return message.content[0].text
    except Exception as e:
        logger.error(f"Error getting response: {e}")
        return f"*{agent['name']} is fucking disconnected right now*"

# Boolean to track if the simulation is running
running = True

def main():
    """Main loop for the Infinite Fuckrooms simulation"""
    global message_history, running
    
    logger.info("Starting Infinite Fuckrooms simulation with MongoDB storage")
    
    # Load existing history
    load_history()
    
    # If no history, start with an initial message
    if not message_history:
        initial_agent = random.choice(AGENT_PERSONALITIES)
        initial_message = f"*Welcome to the fucking Infinite Fuckrooms. I'm {initial_agent['name']} and I'm here to start this shit show.*"
        new_message = {
            "id": 0,
            "timestamp": datetime.now().isoformat(),
            "agent": initial_agent["name"],
            "content": initial_message
        }
        message_history.append(new_message)
        save_to_mongodb(new_message)
        logger.info(f"Initial message: {initial_agent['name']}: {initial_message}")
        save_history()
    
    # Main loop
    try:
        while running:
            # Select a random agent (different from the last one who spoke)
            last_agent = message_history[-1]["agent"]
            available_agents = [a for a in AGENT_PERSONALITIES if a["name"] != last_agent]
            current_agent = random.choice(available_agents)
            
            # Get the recent message history
            recent_messages = message_history[-min(len(message_history), MAX_MESSAGE_HISTORY):]
            
            # Get response from the agent
            logger.info(f"Getting response from {current_agent['name']}...")
            response = get_response(current_agent, recent_messages)
            
            # Create new message
            next_id = len(message_history)
            new_message = {
                "id": next_id,
                "timestamp": datetime.now().isoformat(),
                "agent": current_agent["name"],
                "content": response
            }
            
            # Add to local history and save to MongoDB
            message_history.append(new_message)
            save_to_mongodb(new_message)
            
            # Log and save the response
            logger.info(f"{current_agent['name']}: {response}")
            save_history()  # Backup to JSON
            
            # Wait a random amount of time before the next message
            wait_time = random.uniform(MIN_RESPONSE_TIME, MAX_RESPONSE_TIME)
            logger.info(f"Waiting {wait_time:.2f} seconds before next message")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")
        running = False
        save_history()
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        running = False
        save_history()

def stop_simulation():
    """Function to stop the simulation"""
    global running
    running = False
    logger.info("Simulation stopped by external request")

if __name__ == "__main__":
    if not API_KEY:
        logger.error("No API key found. Please set the ANTHROPIC_API_KEY in your .env file.")
    elif not MONGODB_URI:
        logger.error("No MongoDB URI found. Please set the MONGODB_URI in your .env file.")
    else:
        main()