#!/usr/bin/env python3
"""
Scheduled Task Runner for Telegram Bot
Triggers /run_scheduled_tasks endpoint every hour via GitHub Actions

This script runs automatically via GitHub Actions every hour to execute
scheduled tasks for the Telegram bot by calling the Flask app endpoint.

GitHub Actions Configuration:
- Runs every hour via cron: '0 * * * *'
- Can be manually triggered via workflow_dispatch
- Uses repository secrets for authentication
"""

import os
import sys
import requests
import logging
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduled_tasks.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_env_variables():
    """Load environment variables from .env file or system environment"""
    env_vars = {}
    
    # First try to load from system environment (for GitHub Actions)
    required_vars = [
        'FLASK_APP_URL', 'ADMIN_USERNAME', 'ADMIN_PASSWORD', 
        'TELEGRAM_BOT_TOKEN', 'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'
    ]
    
    # Check if running in GitHub Actions (all vars should be in environment)
    github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    
    if github_actions:
        logger.info("Running in GitHub Actions - loading from environment variables")
        for var in required_vars:
            value = os.getenv(var)
            if value:
                env_vars[var] = value
        
        if len(env_vars) >= 3:  # At least the essential ones
            logger.info(f"Loaded {len(env_vars)} environment variables from system")
            return env_vars
        else:
            logger.error("Missing required environment variables in GitHub Actions")
            return None
    
    # Fallback to .env file for local development
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_file):
        logger.error(f".env file not found at {env_file}")
        logger.info("For GitHub Actions, ensure all secrets are configured")
        logger.info("For local development, copy .env.example to .env and fill in values")
        return None
    
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
        
        logger.info(f"Loaded {len(env_vars)} environment variables from .env file")
        return env_vars
        
    except Exception as e:
        logger.error(f"Error reading .env file: {e}")
        return None

def trigger_scheduled_tasks():
    """Trigger the /run_scheduled_tasks endpoint"""
    try:
        # Load environment variables
        env_vars = load_env_variables()
        if not env_vars:
            logger.error("Failed to load environment variables")
            return False
        
        # Get required configuration
        flask_app_url = env_vars.get('FLASK_APP_URL')
        admin_username = env_vars.get('ADMIN_USERNAME')
        admin_password = env_vars.get('ADMIN_PASSWORD')
        
        if not all([flask_app_url, admin_username, admin_password]):
            logger.error("Missing required environment variables: FLASK_APP_URL, ADMIN_USERNAME, ADMIN_PASSWORD")
            return False
        
        # Construct the endpoint URL
        endpoint_url = f"{flask_app_url.rstrip('/')}/run_scheduled_tasks"
        
        logger.info(f"Triggering scheduled tasks at {endpoint_url}")
        
        # Make the HTTP request with authentication
        response = requests.post(
            endpoint_url,
            auth=(admin_username, admin_password),
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Scheduled tasks executed successfully")
            logger.info(f"📊 Tasks executed: {result.get('tasks_executed', 0)}")
            logger.info(f"📋 Total due tasks: {result.get('total_due_tasks', 0)}")
            
            if result.get('errors'):
                logger.warning(f"⚠️ Some tasks had errors: {result['errors']}")
            
            return True
            
        elif response.status_code == 401:
            logger.error("❌ Authentication failed - check ADMIN_USERNAME and ADMIN_PASSWORD")
            return False
            
        elif response.status_code == 404:
            logger.error("❌ Endpoint not found - check FLASK_APP_URL")
            return False
            
        else:
            logger.error(f"❌ HTTP {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ Request timeout - Flask app may be slow or unresponsive")
        return False
        
    except requests.exceptions.ConnectionError:
        logger.error("❌ Connection error - check FLASK_APP_URL and internet connection")
        return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info(f"🚀 Starting scheduled task runner at {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        success = trigger_scheduled_tasks()
        
        if success:
            logger.info("✅ Scheduled task execution completed successfully")
            exit_code = 0
        else:
            logger.error("❌ Scheduled task execution failed")
            exit_code = 1
            
    except KeyboardInterrupt:
        logger.info("⏹️ Interrupted by user")
        exit_code = 1
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        exit_code = 1
    
    logger.info("=" * 60)
    logger.info(f"🏁 Scheduled task runner finished at {datetime.now()}")
    logger.info("=" * 60)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()