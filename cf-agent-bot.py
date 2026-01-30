#!/usr/bin/env python3
"""
CF Agent AIV2 Bot with Payment Integration

This bot handles both regular commands and payment processing.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import stripe
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app for payment processing
app = Flask(__name__)

# Set Stripe API key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Telegram bot token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


class PaymentBot:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_routes()
        
    def setup_routes(self):
        """Setup Flask routes for payment processing"""
        @self.app.route('/webhook/stripe', methods=['POST'])
        def stripe_webhook():
            payload = request.data
            sig_header = request.headers.get('Stripe-Signature')
            
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
                )
            except ValueError:
                return 'Invalid payload', 400
            except stripe.error.SignatureVerificationError:
                return 'Invalid signature', 400
            
            # Handle the event
            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                logger.info(f'Payment succeeded: {payment_intent["id"]}')
                # Fulfill the purchase
                self.fulfill_order(payment_intent)
            elif event['type'] == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                logger.info(f'Payment failed: {payment_intent["id"]}')
                # Notify the customer about the failure
                self.notify_failure(payment_intent)
            
            return {'status': 'success'}, 200
        
        @self.app.route('/create-payment-intent', methods=['POST'])
        def create_payment_intent():
            try:
                data = request.json
                amount = data.get('amount', 0)
                currency = data.get('currency', 'usd')
                
                intent = stripe.PaymentIntent.create(
                    amount=amount,
                    currency=currency,
                    metadata={
                        'user_id': data.get('user_id'),
                        'product_id': data.get('product_id')
                    }
                )
                
                return jsonify({
                    'client_secret': intent.client_secret,
                    'id': intent.id
                })
            except Exception as e:
                logger.error(f"Error creating payment intent: {str(e)}")
                return jsonify({'error': str(e)}), 400
    
    def fulfill_order(self, payment_intent):
        """Fulfill the order after successful payment"""
        logger.info(f"Fulfilling order for payment: {payment_intent['id']}")
        # Add your order fulfillment logic here
        pass
    
    def notify_failure(self, payment_intent):
        """Notify user about payment failure"""
        logger.info(f"Notifying failure for payment: {payment_intent['id']}")
        # Add notification logic here
        pass


async def start(update, context):
    """Start command handler"""
    await update.message.reply_text(
        'Hello! I am the CF Agent AIV2 Bot with payment integration.\n\n'
        'Commands:\n'
        '/start - Show this message\n'
        '/buy - Purchase premium features\n'
        '/status - Check bot status'
    )


async def buy(update, context):
    """Buy command handler - initiates payment process"""
    await update.message.reply_text(
        'Processing your purchase request...\n'
        'Please contact our support team for premium feature purchases.'
    )
    
    # In a real implementation, this would redirect to a payment page
    # or create a payment intent and send the client secret to the frontend


async def status(update, context):
    """Status command handler"""
    await update.message.reply_text(
        f'Bot Status: Active\n'
        f'Timestamp: {datetime.now().isoformat()}\n'
        f'Payment System: {"Active" if stripe.api_key else "Inactive"}'
    )


def main():
    """Main function to start the bot"""
    # Create payment bot instance
    payment_bot = PaymentBot()
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("status", status))
    
    # Start the bot
    print("Starting CF Agent AIV2 Bot with Payment Integration...")
    
    # Run Flask app in a separate thread for payment processing
    from threading import Thread
    thread = Thread(target=payment_bot.app.run, kwargs={'host': '0.0.0.0', 'port': 5000, 'debug': False, 'use_reloader': False})
    thread.daemon = True
    thread.start()
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == '__main__':
    main()