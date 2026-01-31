# CF AI Agent Matrix Interface

An authentic Matrix-style interface for the CF AI Agent worker bot, featuring the iconic falling green characters animation, terminal interface, and retro cyberpunk aesthetics.

## 🎨 Features

- **Authentic Matrix Rain**: Real-time animated falling characters in the background
- **Terminal Interface**: Interactive command terminal with real responses
- **Status Panels**: Live system status indicators and metrics
- **Cyberpunk Design**: Green-on-black color scheme with glitch effects
- **Responsive Layout**: Works on all device sizes
- **Performance Optimized**: Efficient JavaScript with smooth animations
- **Interactive Elements**: Working command terminal and status indicators

## 📱 Preview

The interface includes:
- Animated Matrix background with falling Japanese/Katakana characters
- Glitch-effect title text with flickering animation
- Working terminal that responds to commands
- Status panels showing system metrics
- Scan line animation for authentic CRT effect
- Interactive command input with EXEC button

## 🛠️ Commands Available

The terminal supports these commands:
- `status` - Shows agent status and worker statistics
- `scan` - Initiates network scanning simulation
- `workers` - Lists active workers
- `help` - Shows available commands
- `protect` - Activates protective protocols
- `analyze` - Starts deep analysis simulation
- `report` - Generates security report

## 🚀 Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
# Or directly:
node server.js
```

Visit `http://localhost:3000` to see the Matrix interface.

### Production Deployment

The site is configured for easy deployment to Cloudflare:

1. Push code to GitHub repository
2. Connect to Cloudflare Pages
3. Configure custom domain
4. Enjoy global CDN and SSL

## ☁️ Cloudflare Deployment

### Deploy to Cloudflare Pages

1. Fork or create a GitHub repository with this code
2. Go to Cloudflare Dashboard > Pages
3. Click "Create a project"
4. Connect your GitHub repository
5. Set build settings:
   - Build command: `npm install && echo 'Static site'`
   - Build output directory: `.`
   - Root directory: `.`

### Deploy to Cloudflare Workers

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Deploy
wrangler deploy
```

## 🎯 Design Elements

- **Color Scheme**: Black background with bright green text (#0f0)
- **Typography**: Monospace 'Courier New' font for authentic terminal feel
- **Animations**: 
  - Falling character matrix rain
  - Pulsing status indicators
  - CRT scan line effect
  - Text flicker/glitch effects
- **Layout**: Grid-based panel system with status indicators
- **Effects**: 
  - Text shadow glow
  - Pseudo-3D depth with borders
  - Smooth terminal interactions

## 📱 Responsive Design

The interface adapts to all screen sizes:
- Desktop: Full dual-panel layout
- Tablet: Adjusted panel sizing
- Mobile: Stacked vertical layout

## ⚡ Performance

- Optimized canvas rendering for matrix animation
- Efficient JavaScript with requestAnimationFrame
- Lightweight implementation
- Fast loading times

## 🔧 Customization

### Colors
- Primary: `#0f0` (bright green)
- Secondary: `#0a0` (darker green)
- Background: `#000` (black)

### Animation Speed
Adjust the matrix rain speed by changing the interval in the `setInterval(drawMatrix, 33)` call.

### Character Set
Modify the `chars` variable in the JavaScript to change the falling characters.

## 🛡️ Security

- All resources served over HTTPS in production
- Input validation in the terminal simulation
- Prepared for integration with real security features

## 📞 Support

For issues with deployment or customization, refer to:
- `DEPLOYMENT.md` for detailed Cloudflare setup
- Cloudflare documentation for platform-specific issues

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤖 About CF AI Agent

The CF AI Agent Matrix Interface provides a visually striking and immersive experience for interacting with Cloudflare worker bots. The design combines nostalgic Matrix aesthetics with modern web technologies to create an engaging interface for AI agent interaction.