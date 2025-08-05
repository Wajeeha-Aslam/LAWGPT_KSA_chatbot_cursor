# env_config_sample.py
# Copy this file to env_config.py and fill in your actual credentials

import os

# Azure OpenAI Configuration
os.environ["AZURE_OPENAI_KEY"] = "YOUR_AZURE_OPENAI_KEY_HERE"
os.environ["AZURE_OPENAI_ENDPOINT"] = "YOUR_AZURE_OPENAI_ENDPOINT_HERE"
os.environ["AZURE_OPENAI_VERSION"] = "2024-12-01-preview"

# Qdrant Cloud Configuration
os.environ["QDRANT_URL"] = "YOUR_QDRANT_CLOUD_URL_HERE"
os.environ["QDRANT_API_KEY"] = "YOUR_QDRANT_API_KEY_HERE"

# MongoDB Configuration (optional)
os.environ["MONGODB_URI"] = "YOUR_MONGODB_URI_HERE" 