"""
test_connection.py
──────────────────
Verifies Firebase connectivity and State Bus functionality.
"""

import os
import uuid
import logging
import sys
from datetime import datetime

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ConnectionTest")

try:
    from state_bus import SharedStateBus
    from schemas import Message, MessageType
except ImportError as e:
    logger.error(f"Failed to import project modules: {e}")
    logger.info("Make sure you have pydantic and firebase-admin installed: pip install pydantic firebase-admin")
    sys.exit(1)

def run_test():
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    logger.info(f"Starting connection test with session: {session_id}")
    
    try:
        # Initialize the bus
        # This will trigger Firebase initialization and create the session path
        bus = SharedStateBus(session_id)
        logger.info("Successfully initialized SharedStateBus.")
        
        # Create a test message
        test_msg = Message(
            message_id=str(uuid.uuid4()),
            sender="connection_tester",
            msg_type=MessageType.HEARTBEAT,
            content={
                "status": "online",
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Testing Firebase connectivity from Antigravity"
            }
        )
        
        # Push the message
        bus.push_message(test_msg)
        logger.info("Successfully pushed test message to Firebase.")
        
        # Verify message exists (optional but good)
        # Note: We use .get() which is synchronous
        data = bus.db_ref.child("messages").get()
        if data:
            logger.info("Verified: Messages found in database.")
            for msg_id, msg_data in data.items():
                logger.info(f"  - Message ID: {msg_id}, Sender: {msg_data.get('sender')}")
        else:
            logger.warning("Push succeeded but no messages found on read. Check database rules.")
            
        print("\n" + "="*50)
        print("✅ CONNECTION TEST SUCCESSFUL!")
        print(f"Session ID: {session_id}")
        print(f"Path: /sessions/{session_id}")
        print("="*50 + "\n")
        
    except FileNotFoundError as e:
        logger.error(f"Firebase Configuration Error: {e}")
        print("\n❌ FAILED: serviceAccountKey.json not found.")
        print("Please place your Firebase service account key in the project root.")
    except ValueError as e:
        logger.error(f"Firebase Configuration Error: {e}")
        print(f"\n❌ FAILED: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ FAILED: An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_test()
