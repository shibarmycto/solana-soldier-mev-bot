# CF Agent AIV2 Bot Service Setup

## Overview
This setup creates a persistent background service for the CF Agent AIV2 bot on macOS using launchd (macOS equivalent of systemd).

## Components Created

1. **Launch Agent Plist**: `~/Library/LaunchAgents/com.cf.agent.aiv2.bot.plist`
   - Runs the Telegram bot using `run_bot.sh`
   - Starts automatically at boot
   - Restarts automatically if it crashes
   - Logs output to `/Users/anthonypium/clawd/logs/`

2. **Management Script**: `manage_bot_service.sh`
   - Provides easy commands to manage the service

## Service Configuration Details

- **Label**: com.cf.agent.aiv2.bot
- **Program**: /bin/bash /Users/anthonypium/clawd/run_bot.sh
- **Working Directory**: /Users/anthonypium/clawd
- **Auto-start**: Yes (RunAtLoad = true)
- **Auto-restart**: Yes (KeepAlive on failure)
- **Logs**: 
  - stdout: /Users/anthonypium/clawd/logs/bot.stdout.log
  - stderr: /Users/anthonypium/clawd/logs/bot.stderr.log

## Management Commands

```bash
# Start the service
./manage_bot_service.sh start

# Stop the service
./manage_bot_service.sh stop

# Restart the service
./manage_bot_service.sh restart

# Check service status
./manage_bot_service.sh status

# View recent logs
./manage_bot_service.sh logs
```

## Notes

- The service runs as the current user (anthonypium)
- The bot uses the configuration from config.json in the clawd directory
- The service will automatically start when the system boots
- The service will automatically restart if it crashes or exits unexpectedly