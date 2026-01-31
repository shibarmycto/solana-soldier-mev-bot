# Deployment Guide for Solana Soldier MEV Bot Website

This guide explains how to deploy the Solana Soldier MEV Bot website with CF Dev (Cloudflare Workers) and configure Cloudflare CDN.

## Prerequisites

1. **Cloudflare Account**: Sign up at [cloudflare.com](https://cloudflare.com)
2. **Cloudflare Workers CLI**: Install Wrangler with `npm install -g wrangler`
3. **GitHub Repository**: To connect with Cloudflare Pages

## Deployment Steps

### 1. Deploy with Cloudflare Pages (Recommended)

```bash
# Navigate to project directory
cd solana-soldier-mevbot

# Create a GitHub repository with your code
# 1. Initialize git: git init
# 2. Add files: git add .
# 3. Commit: git commit -m "Initial commit"
# 4. Create repo on GitHub and push

# Alternatively, you can deploy manually:
npx wrangler pages deploy . --project-name=solana-soldier-mevbot
```

### 2. Configure Custom Domain with Cloudflare

1. In your Cloudflare dashboard, go to "Workers & Pages"
2. Select your deployed project
3. Navigate to "Custom domains" 
4. Add your custom domain: `solanasoldiermevbot.yourdomain.com`

### 3. Update DNS Settings

1. Go to your domain registrar (where you purchased the domain)
2. Update the nameservers to the ones provided by Cloudflare (if you're using Cloudflare DNS)
3. OR add a CNAME record pointing your subdomain to your Cloudflare Workers/Pages deployment
4. Wait for DNS propagation (can take up to 48 hours, usually 1-4 hours)

### 4. Configure Cloudflare Settings

Once DNS is pointing to Cloudflare:

1. Go to "DNS" settings in Cloudflare
2. Verify that the A record or CNAME record points to your Cloudflare deployment
3. Go to "SSL/TLS" and set encryption mode to "Full"
4. Enable "Always Use HTTPS"
5. Go to "Speed" and enable "Optimization"
6. Go to "Security" and adjust according to your needs

## Alternative: Cloudflare Workers Sites

If you prefer using Cloudflare Workers directly:

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create a new Workers project
wrangler init solana-soldier-mevbot
cd solana-soldier-mevbot

# Update wrangler.toml to use static site configuration
# Then deploy:
wrangler deploy
```

## Verification

1. Visit your domain to ensure the site loads properly
2. Check that SSL certificate is valid
3. Verify that all assets (CSS, JS) are loading correctly
4. Test all interactive elements

## Troubleshooting

### Common Issues:

1. **Site not loading after DNS change**: Wait for DNS propagation
2. **SSL Certificate errors**: Check Cloudflare SSL/TLS settings
3. **Assets not loading**: Verify paths in HTML files
4. **Mixed content warnings**: Ensure all resources use HTTPS

### Cloudflare Analytics:

Check the Cloudflare dashboard for traffic analytics and performance metrics.

## Updating the Site

To update the deployed site:

1. Make changes to your files
2. Push changes to your connected GitHub repository
3. Cloudflare Pages will automatically rebuild and deploy

The site will automatically rebuild and deploy the new version.