import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_client import BaseClient
import os

# Initialize Firebase Admin SDK
def initialize_firebase():
    # Check if already initialized
    if not firebase_admin._apps:
        # Check for service account key in environment variable or file
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
        elif "FIREBASE_SERVICE_ACCOUNT_KEY_JSON" in os.environ:
            # The environment variable contains the JSON string of the key
            import json
            service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_KEY_JSON"])
            cred = credentials.Certificate(service_account_info)
        else:
            raise FileNotFoundError(
                "Firebase service account key not found. "
                "Either provide a 'serviceAccountKey.json' file or set the "
                "'FIREBASE_SERVICE_ACCOUNT_KEY_JSON' environment variable."
            )
        firebase_admin.initialize_app(cred)
    
    # Return Firestore client
    return firestore.client()

# Firestore client instance
db = initialize_firebase()