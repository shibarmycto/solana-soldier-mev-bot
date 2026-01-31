#!/bin/bash

# Digital Ocean Server Setup Script for Clawdbot, Agent-Zero, and Moltbot
# Includes PayPal integration, terminal rental system, and Cloudflare tunnel

set -e  # Exit on any error

echo "Starting Digital Ocean server setup..."
echo "Server IP: 104.248.171.85"

# Update system packages
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required dependencies
echo "Installing required dependencies..."
sudo apt install -y curl wget git unzip build-essential python3 python3-pip nodejs npm nginx certbot python3-certbot-nginx

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create project directory
PROJECT_DIR="/opt/clawdbot"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# Clone repositories
echo "Cloning repositories..."
git clone https://github.com/clawdbot/clawdbot.git ./clawdbot
git clone https://github.com/agent-zero/agent-zero.git ./agent-zero
git clone https://github.com/moltbot/moltbot.git ./moltbot

# Install Node.js dependencies
echo "Installing Node.js dependencies..."

# Install clawdbot dependencies
cd $PROJECT_DIR/clawdbot
npm install

# Install agent-zero dependencies
cd $PROJECT_DIR/agent-zero
npm install

# Install moltbot dependencies
cd $PROJECT_DIR/moltbot
npm install

# Set up PayPal integration
echo "Setting up PayPal integration..."
mkdir -p $PROJECT_DIR/config

cat > $PROJECT_DIR/config/paypal.json << 'EOF'
{
  "clientId": "AUXeCwiB5vzBsKb6sun7nE-TP7KC_EhmKZuM5C40FkyebSYb0tD-pafCIBo-ab2sF_PrPaHVPItixMy9",
  "clientSecret": "",
  "mode": "live"
}
EOF

# Create payment processing system
cat > $PROJECT_DIR/payment_system.js << 'EOF'
const paypal = require('@paypal/checkout-server-sdk');
const fs = require('fs');

// Load PayPal config
const paypalConfig = JSON.parse(fs.readFileSync('/opt/clawdbot/config/paypal.json', 'utf8'));

// Environment setup
let environment;
if (paypalConfig.mode === 'sandbox') {
    environment = new paypal.core.SandboxEnvironment(
        paypalConfig.clientId,
        paypalConfig.clientSecret
    );
} else {
    environment = new paypal.core.LiveEnvironment(
        paypalConfig.clientId,
        paypalConfig.clientSecret
    );
}

const client = new paypal.core.PayPalHttpClient(environment);

// Terminal rental pricing
const PRICING = {
    terminal_rental: {
        daily: 20.00, // £20 per day
        monthly: 500.00 // £500 per month
    }
};

async function createPayment(amount, description, returnUrl, cancelUrl) {
    const request = new paypal.orders.OrdersCreateRequest();
    request.prefer('return=representation');
    request.requestBody({
        intent: 'CAPTURE',
        purchase_units: [{
            amount: {
                currency_code: 'GBP',
                value: amount
            },
            description: description
        }],
        application_context: {
            return_url: returnUrl,
            cancel_url: cancelUrl
        }
    });

    try {
        const order = await client.execute(request);
        return order.result;
    } catch (err) {
        console.error('Error creating payment:', err);
        throw err;
    }
}

async function capturePayment(orderId) {
    const request = new paypal.orders.OrdersCaptureRequest(orderId);
    request.requestBody({});

    try {
        const response = await client.execute(request);
        return response.result;
    } catch (err) {
        console.error('Error capturing payment:', err);
        throw err;
    }
}

module.exports = {
    createPayment,
    capturePayment,
    PRICING
};
EOF

# Create terminal rental system
cat > $PROJECT_DIR/terminal_rental.js << 'EOF'
const { createPayment, capturePayment, PRICING } = require('./payment_system');
const fs = require('fs');
const path = require('path');

class TerminalRentalSystem {
    constructor() {
        this.rentalsFile = path.join(__dirname, 'rentals.json');
        this.ensureRentalsFile();
    }

    ensureRentalsFile() {
        if (!fs.existsSync(this.rentalsFile)) {
            fs.writeFileSync(this.rentalsFile, JSON.stringify([]));
        }
    }

    async rentTerminal(userId, duration) {
        // Duration in days
        let amount, description;
        
        if (duration === 'daily') {
            amount = PRICING.terminal_rental.daily;
            description = 'AI Terminal Rental - 24 hours';
        } else if (duration === 'monthly') {
            amount = PRICING.terminal_rental.monthly;
            description = 'AI Terminal Rental - Monthly Subscription';
        } else {
            throw new Error('Invalid duration. Use "daily" or "monthly"');
        }

        const returnUrl = `http://localhost:3000/payment/success`;
        const cancelUrl = `http://localhost:3000/payment/cancel`;

        const payment = await createPayment(amount, description, returnUrl, cancelUrl);
        return {
            userId,
            orderId: payment.id,
            amount,
            duration,
            status: 'pending',
            createdAt: new Date().toISOString()
        };
    }

    async completeRental(paymentData) {
        const capturedPayment = await capturePayment(paymentData.orderId);
        
        if (capturedPayment.status === 'COMPLETED') {
            // Add rental to active rentals
            const rentals = JSON.parse(fs.readFileSync(this.rentalsFile, 'utf8'));
            
            const rental = {
                userId: paymentData.userId,
                orderId: paymentData.orderId,
                amount: paymentData.amount,
                duration: paymentData.duration,
                status: 'active',
                startDate: new Date().toISOString(),
                endDate: this.calculateEndDate(paymentData.duration),
                createdAt: new Date().toISOString()
            };
            
            rentals.push(rental);
            fs.writeFileSync(this.rentalsFile, JSON.stringify(rentals, null, 2));
            
            return rental;
        }
        
        throw new Error('Payment capture failed');
    }

    calculateEndDate(duration) {
        const now = new Date();
        if (duration === 'daily') {
            now.setDate(now.getDate() + 1);
        } else if (duration === 'monthly') {
            now.setMonth(now.getMonth() + 1);
        }
        return now.toISOString();
    }

    getActiveRentals() {
        const rentals = JSON.parse(fs.readFileSync(this.rentalsFile, 'utf8'));
        return rentals.filter(rental => 
            rental.status === 'active' && 
            new Date(rental.endDate) > new Date()
        );
    }
}

module.exports = TerminalRentalSystem;
EOF

# Create systemd services for persistence
echo "Creating systemd services..."

sudo tee /etc/systemd/system/clawdbot.service << 'EOF'
[Unit]
Description=Clawdbot Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/clawdbot/clawdbot
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/agent-zero.service << 'EOF'
[Unit]
Description=Agent-Zero Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/clawdbot/agent-zero
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/moltbot.service << 'EOF'
[Unit]
Description=Moltbot Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/clawdbot/moltbot
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Install Cloudflare Tunnel
echo "Installing Cloudflare Tunnel..."
curl -fsSL https://pkg.cloudflare.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-archive-keyring.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update && sudo apt install -y cloudflared

# Initialize Cloudflare Tunnel
echo "Initializing Cloudflare Tunnel..."
cloudflared tunnel login

echo "Setup script completed!"
echo "Next steps:"
echo "1. Run 'cloudflared tunnel create your-tunnel-name' to create a tunnel"
echo "2. Update your domain DNS records as prompted"
echo "3. Create a config file at ~/.cloudflared/config.yml with your tunnel details"
echo "4. Enable and start the services:"
echo "   sudo systemctl enable clawdbot agent-zero moltbot"
echo "   sudo systemctl start clawdbot agent-zero moltbot"
echo ""
echo "For the terminal interface with AI agents that survive wipes:"
echo "- Data will be stored in $PROJECT_DIR/data directory"
echo "- Configuration files will persist across reboots"
echo "- Services will automatically restart on system boot"