import os
from flask import Flask, render_template, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# Initialize MongoDB client
MONGODB_URI = os.environ.get("MONGODB_URI", "")
try:
    client = MongoClient(MONGODB_URI)
    db = client.fuckrooms
    messages_collection = db.messages
    # Test the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    client = None
    db = None
    messages_collection = None

# Route for the main page
@app.route('/')
def index():
    return render_template('index.html')

# API endpoint to get all messages
@app.route('/api/messages')
def get_messages():
    if messages_collection is not None:
        try:
            # Get all messages from MongoDB, sorted by ID
            messages = list(messages_collection.find({}, {"_id": 0}).sort("id", 1))
            return jsonify(messages)
        except Exception as e:
            print(f"Error fetching messages: {e}")
            return jsonify([])
    else:
        return jsonify([])

# API endpoint to get new messages (for polling)
@app.route('/api/new_messages/<last_id>')
def get_new_messages(last_id):
    if messages_collection is not None:
        try:
            # Convert last_id to integer, handling special cases
            try:
                last_id_int = int(last_id)
            except ValueError:
                if last_id.lower() == 'nan' or last_id == '-1':
                    last_id_int = -1
                else:
                    last_id_int = -1

            # Get new messages (greater than last_id)
            new_messages = list(messages_collection.find(
                {"id": {"$gt": last_id_int}}, 
                {"_id": 0}
            ).sort("id", 1))
            
            return jsonify(new_messages)
        except Exception as e:
            print(f"Error in get_new_messages: {e}")
            return jsonify([])
    else:
        return jsonify([])

# Health check endpoint
@app.route('/api/health')
def health_check():
    mongodb_status = "connected" if messages_collection is not None else "disconnected"
    return jsonify({
        "status": "ok",
        "mongodb": mongodb_status
    })

# For local development
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)