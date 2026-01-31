import json
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Load configuration from config.json
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    BOT_TOKEN = config['bot_token']
    TARGET_GROUP_ID = config['target_group_id']
    TRIGGER_PHRASE = config['trigger_phrase']
    RESPONSE_MESSAGE = config['response_message']
    
except FileNotFoundError:
    logger.error("Config file 'config.json' not found. Please create it with your bot token.")
    exit(1)
except KeyError as e:
    logger.error(f"Missing key in config.json: {e}")
    exit(1)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    # Get message details
    message = update.message
    
    # Ensure we have a message and text
    if not message or not message.text:
        return
        
    chat_id = message.chat_id
    
    # Only process messages from the target group
    if chat_id != TARGET_GROUP_ID:
        return
    
    # Check if message contains the trigger phrase (case-insensitive)
    if TRIGGER_PHRASE.upper() in message.text.upper():
        # Reply directly to the specific message
        await message.reply_text(RESPONSE_MESSAGE)
        logger.info(f"Replied to message from user {message.from_user.id} in group {chat_id}")

def main():
    """Start the bot"""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add message handler for text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    logger.info("Starting bot...")
    logger.info(f"Monitoring group: {TARGET_GROUP_ID}")
    logger.info(f"Trigger phrase: '{TRIGGER_PHRASE}'")
    application.run_polling()

if __name__ == '__main__':
    main()