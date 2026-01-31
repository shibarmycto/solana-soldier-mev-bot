# CF AI Agent Matrix Interface Deployment Guide

This guide explains how to deploy the Matrix-style CF AI Agent interface with Cloudflare Workers and Pages.

## Prerequisites

1. **Cloudflare Account**: Sign up at [cloudflare.com](https://cloudflare.com)
2. **Cloudflare Workers CLI**: Install Wrangler with `npm install -g wrangler`
3. **Git Repository**: To connect with Cloudflare Pages

## Deployment Methods

### Method 1: Cloudflare Pages (Recommended for Static Sites)

For the Matrix-style interface which is primarily static:

```bash
# Navigate to project directory
cd cf-ai-agent

# Create a GitHub repository with your code
# 1. Initialize git: git init
# 2. Add files: git add .
# 3. Commit: git commit -m "Initial Matrix Interface"
# 4. Create repo on GitHub and push

# Connect to Cloudflare Pages via dashboard:
# 1. Go to Cloudflare Dashboard > Pages
# 2. Click "Create a project"
# 3. Connect your GitHub repository
# 4. Set build settings:
#    - Build command: "npm install && echo 'Static site'"
#    - Build output directory: "."
#    - Root directory: "."
```

### Method 2: Cloudflare Workers (For Dynamic Features)

If you want to add dynamic features to the Matrix interface:

```bash
# Install Wrangler globally
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create a new Workers project
wrangler init cf-ai-agent
cd cf-ai-agent

# Replace the default wrangler.toml with the one provided
# Then deploy:
wrangler deploy
```

### Method 3: Local Development

For testing locally:

```bash
# Install dependencies
npm install

# Start development server
npm run dev
# Or directly:
node server.js
```

## Configuration

### Custom Domain Setup

1. In your Cloudflare dashboard, go to "Workers & Pages"
2. Select your deployed project
3. Navigate to "Custom domains"
4. Add your custom domain: `cf-ai-agent.yourdomain.com`

### DNS Configuration

1. Go to your domain registrar
2. Update nameservers to Cloudflare's nameservers (if using Cloudflare DNS)
3. OR add a CNAME record pointing your subdomain to your Cloudflare deployment
4. Wait for DNS propagation (1-4 hours typically)

### SSL/TLS Settings

1. Go to "SSL/TLS" in Cloudflare dashboard
2. Set encryption mode to "Full"
3. Enable "Always Use HTTPS"
4. Turn on "Automatic HTTPS Rewrites"

## Environment Variables (if using Workers)

```bash
# Set environment variables via Wrangler
wrangler secret put YOUR_SECRET_NAME
```

Or in wrangler.toml:

```toml
[vars]
NODE_ENV = "production"
SITE_TITLE = "CF AI Agent Matrix Interface"
```

## Verification

1. Visit your domain to ensure the Matrix rain animation loads
2. Check that terminal commands work in the interface
3. Verify all interactive elements function properly
4. Test responsive design on different screen sizes

## Troubleshooting

### Common Issues:

1. **Matrix animation not appearing**: Check browser console for JavaScript errors
2. **Terminal commands not working**: Verify JavaScript is enabled
3. **Slow loading**: Optimize images and assets
4. **Mobile responsiveness**: Test on various screen sizes

### Performance Optimization:

- Minimize JavaScript for faster loading
- Optimize canvas rendering performance
- Use efficient CSS animations
- Implement proper caching headers

## Updating the Site

To update your deployed site:

### For Cloudflare Pages:
1. Make changes to your local files
2. Commit and push to your connected GitHub repository
3. Cloudflare Pages will automatically rebuild and deploy

### For Cloudflare Workers:
1. Make changes to your files
2. Run: `wrangler deploy`
3. Changes will be live immediately

## Security Considerations

The Matrix interface includes security-focused design elements but actual security depends on your backend implementation:

1. Use HTTPS for all connections
2. Implement proper authentication for sensitive operations
3. Validate all user inputs
4. Regularly update dependencies