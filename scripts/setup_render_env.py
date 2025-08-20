#!/usr/bin/env python3
"""
Render Environment Variables Setup Script
Helps configure environment variables for Project Archangel deployment
"""

import os
import sys

def print_environment_setup():
    """Print the environment variables needed for Render"""
    
    print("🔧 Project Archangel - Render Environment Variables Setup")
    print("=" * 60)
    print()
    
    print("📋 Copy these environment variables to your Render service:")
    print()
    
    env_vars = {
        # ClickUp Integration
        "CLICKUP_TOKEN": "pk_132000182_VEWS6RMM30M2794Q20J7HEWG9IOP2L7M",
        "CLICKUP_TEAM_ID": "9013769810",
        "CLICKUP_LIST_ID": "901317725718",
        "CLICKUP_WEBHOOK_SECRET": "YOUR_WEBHOOK_SECRET_HERE",  # Will be set after webhook creation
        
        # Application Settings
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "INFO",
        "PORT": "8080",
        "TRACING_ENABLED": "false",
        "SERENA_ENABLED": "false",
        "PUBLIC_BASE_URL": "https://project-archangel-api.onrender.com",
        
        # Security
        "JWT_SECRET_KEY": "your-super-secret-jwt-key-change-this-in-production",
        "ENCRYPTION_KEY": "your-32-byte-encryption-key-change-this",
        
        # Optional Provider Settings
        "TRELLO_KEY": "",
        "TRELLO_TOKEN": "",
        "TRELLO_LIST_ID": "",
        "TRELLO_WEBHOOK_SECRET": "",
        "TODOIST_TOKEN": "",
        "TODOIST_PROJECT_ID": "",
        "TODOIST_WEBHOOK_SECRET": "",
    }
    
    for key, value in env_vars.items():
        print(f"{key}={value}")
    
    print()
    print("📝 Instructions:")
    print("1. Go to your Render dashboard")
    print("2. Select your project-archangel-api service")
    print("3. Go to 'Environment' tab")
    print("4. Add each variable above")
    print("5. Save and redeploy")
    print()
    print("⚠️  Important:")
    print("- Replace YOUR_WEBHOOK_SECRET_HERE with the actual webhook secret")
    print("- Change the security keys for production use")
    print("- Set TRELLO_* and TODOIST_* variables if you want those integrations")

def print_webhook_creation():
    """Print the webhook creation command"""
    
    print()
    print("🔗 ClickUp Webhook Creation")
    print("=" * 40)
    print()
    print("After setting environment variables, create the webhook:")
    print()
    
    webhook_command = '''curl --request POST \\
     --url https://api.clickup.com/api/v2/team/9013769810/webhook \\
     --header 'accept: application/json' \\
     --header 'content-type: application/json' \\
     --header 'Authorization: pk_132000182_VEWS6RMM30M2794Q20J7HEWG9IOP2L7M' \\
     --data '{
  "events": [
    "taskCreated",
    "taskUpdated", 
    "taskDeleted",
    "taskCommentPosted",
    "taskStatusUpdated",
    "taskPriorityUpdated",
    "taskAssigneeUpdated",
    "taskDueDateUpdated",
    "taskMoved"
  ],
  "endpoint": "https://project-archangel-api.onrender.com/webhooks/clickup",
  "list_id": 901317725718
}'
'''
    
    print(webhook_command)
    print()
    print("📝 Steps:")
    print("1. Run the webhook creation command")
    print("2. Copy the 'secret' from the response")
    print("3. Add CLICKUP_WEBHOOK_SECRET=your_secret to Render environment")
    print("4. Redeploy the service")

if __name__ == "__main__":
    print_environment_setup()
    print_webhook_creation()
