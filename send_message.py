#!/usr/bin/env python3
"""
Simple terminal client to send messages to the AI Village
"""

import requests
import json
import sys

def send_message(message):
    """Send message to server"""
    try:
        response = requests.post(
            "http://localhost:8000/message",
            json={"message": message},
            headers={"Content-Type": "application/json"}
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_messages():
    """Get recent messages from server"""
    try:
        response = requests.get("http://localhost:8000/messages")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_message.py 'your message here'")
        print("       python send_message.py --get (to see recent messages)")
        sys.exit(1)
    
    if sys.argv[1] == "--get":
        result = get_messages()
        print(json.dumps(result, indent=2))
    else:
        message = " ".join(sys.argv[1:])
        result = send_message(message)
        print(json.dumps(result, indent=2))
