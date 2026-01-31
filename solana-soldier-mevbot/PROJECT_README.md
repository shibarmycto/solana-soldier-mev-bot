# Solana Soldier MEV Bot Website

This is a complete replica of the Solana Soldier MEV Bot landing page with all the design elements, functionality, and styling from the reference website, built by CF Dev with Cloudflare technology.

## 🎨 Features

- **Authentic Design**: Exact replica of the reference website with dark theme and purple/teal gradients
- **Responsive Layout**: Works perfectly on mobile and desktop devices
- **Interactive Elements**: Functional buttons with hover effects and animations
- **Modern UI**: Crypto/web3 aesthetic with gradient accents and sleek typography
- **Performance Optimized**: Lightweight implementation with efficient CSS and minimal JavaScript

## 📋 Contents

- `index.html`: Main landing page with all styling and scripting embedded
- `server.js`: Express server for serving the static site
- `package.json`: Dependencies and deployment scripts
- `railway.toml`: Railway deployment configuration
- `DEPLOYMENT.md`: Complete guide for deploying to Railway with Cloudflare

## 🚀 Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
# Or directly with Node
PORT=3000 node server.js
```

Visit `http://localhost:3000` to see the site.

### Production Deployment

The site is configured for easy deployment to Railway with Cloudflare CDN:

1. Push code to GitHub repository
2. Connect to Railway and deploy
3. Configure custom domain in Railway
4. Set up Cloudflare for CDN and SSL

## 🎯 Design Elements Replicated

- **Dark Gradient Background**: Black to deep purple/indigo gradient
- **Logo**: Shield icon with purple-to-teal gradient
- **Typography**: Bold "SOLANA SOLDIER" branding
- **CTA Buttons**: "LAUNCH BOT" gradient button with lightning bolt
- **Hero Section**: "AUTOMATED SOLANA ARBITRAGE TRADING" with gradient text
- **Subheading**: "Track whole wallets..." description
- **Primary CTA**: "GET STARTED" gradient button with lightning bolt
- **Secondary CTA**: "LEARN MORE" outlined button
- **Footer**: "Live Stats" section with "Made with Emergent" badge

## ☁️ Deployment to Railway + Cloudflare

### Step 1: Prepare for Railway Deployment

1. Create a new GitHub repository with this code
2. Sign up for Railway at [railway.app](https://railway.app)
3. Install Railway CLI: `npm install -g @railway/cli`

### Step 2: Deploy to Railway

```bash
# Login to Railway
railway login

# Link to your project
railway init

# Deploy
railway up
```

### Step 3: Configure Custom Domain

In Railway dashboard:
1. Go to Settings > Domains
2. Add custom domain: `solanasoldiermevbot.yourdomain.com`

### Step 4: Set Up Cloudflare

1. Log into Cloudflare
2. Add your domain to Cloudflare
3. Update your domain's nameservers to Cloudflare's nameservers
4. In Cloudflare, ensure the DNS record points to your Railway deployment

## 🔧 Customization

### Colors
- Primary gradient: `linear-gradient(135deg, #7b61ff 0%, #00ffc4 100%)`
- Background: `linear-gradient(135deg, #0a0a0a 0%, #0d0d1a 50%, #1a0d1a 100%)`
- Text: White with varying opacity

### Typography
- Font family: Inter, with fallbacks to system fonts
- Headings: Large, bold with gradient text effect
- Body text: Medium gray for secondary information

## 📱 Responsive Design

The site is optimized for all screen sizes:
- Mobile-first approach
- Flexible grid system
- Appropriate spacing on small screens
- Readable typography at all sizes

## ⚡ Performance

- Minimal JavaScript
- Efficient CSS with gradients and animations
- Optimized asset delivery
- Fast loading times

## 🛡️ Security

- All resources served over HTTPS in production
- Sanitized user inputs (though this is primarily a static site)
- Prepared for SSL/TLS via Cloudflare

## 📞 Support

For issues with deployment or customization, refer to:
- `DEPLOYMENT.md` for detailed Railway/Cloudflare setup
- Railway documentation for platform-specific issues
- Cloudflare documentation for CDN/SSL setup

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.