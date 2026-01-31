# Railway Deployment Information for Claude Remote Assistant Bot

## Prerequisites

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

Or install via Homebrew:
```bash
brew install railway
```

## Login to Railway

1. Login to Railway using the CLI:
```bash
railway login
```
This will open a browser window for authentication.

## Deploy the Claude Remote Assistant Bot

1. Navigate to the project directory:
```bash
cd claude-remote-assistant
```

2. Login to Railway (if not already logged in):
```bash
railway login
```

3. Link the project to a new Railway service:
```bash
railway init
```
Choose "Create a new project" and give it a name like "claude-remote-assistant".

4. Set environment variables:
```bash
railway up
```
Then add these variables in the Railway dashboard or CLI:
- TELEGRAM_BOT_TOKEN=7862446311:AAEylZynz3QSfWE_5GKCFYcTeMCOn8DJS98
- ANTHROPIC_API_KEY=[Your Claude API key]
- ENCRYPTION_KEY=[Generate a strong encryption key]

To set via CLI:
```bash
railway vars set TELEGRAM_BOT_TOKEN="7862446311:AAEylZynz3QSfWE_5GKCFYcTeMCOn8DJS98"
railway vars set ANTHROPIC_API_KEY="[Your Claude API key]"
railway vars set ENCRYPTION_KEY="[Generate a strong encryption key]"
```

5. Deploy to Railway:
```bash
railway up
```

## Alternative: Connect GitHub Repository

1. Push the claude-remote-assistant directory to a GitHub repository:
```bash
cd claude-remote-assistant
git init
git add .
git commit -m "Initial commit for Railway deployment"
git remote add origin [your-github-repo-url]
git push -u origin main
```

2. Go to https://railway.app and connect your GitHub account
3. Select "New Project" and choose "Deploy from GitHub"
4. Select your repository containing the Claude Remote Assistant Bot
5. Railway will automatically detect the project and deploy it
6. Add the environment variables in the Railway dashboard under "Variables"

## Required Environment Variables

- `TELEGRAM_BOT_TOKEN`: 7862446311:AAEylZynz3QSfWE_5GKCFYcTeMCOn8DJS98
- `ANTHROPIC_API_KEY`: [Your Claude API key]
- `ENCRYPTION_KEY`: [Generate a strong encryption key - you can use: openssl rand -base64 32]

## Configuration Notes

- The project includes a `railway.json` file that configures the deployment
- The `Dockerfile` ensures proper containerization
- The `Procfile` specifies the startup command
- Dependencies are managed via `requirements.txt`

## Accessing Logs

To view logs after deployment:
```bash
railway logs
```

## Updating the Deployment

After making changes and pushing to GitHub:
```bash
railway up
```

Or if using GitHub integration, commits to the main branch will automatically trigger deployments.

## Troubleshooting

- If deployment fails, check the logs with `railway logs`
- Ensure all required environment variables are set
- Verify that the port specified in railway.json matches what the application uses (typically 8080)