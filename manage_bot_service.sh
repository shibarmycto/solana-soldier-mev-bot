#!/bin/bash

# Script to manage the CF Agent AIV2 bot service on macOS

SERVICE_NAME="com.cf.agent.aiv2.bot"
PLIST_PATH="$HOME/Library/LaunchAgents/$SERVICE_NAME.plist"

case "$1" in
    start)
        echo "Starting CF Agent AIV2 bot service..."
        launchctl load "$PLIST_PATH"
        echo "Service started."
        ;;
    stop)
        echo "Stopping CF Agent AIV2 bot service..."
        launchctl unload "$PLIST_PATH"
        echo "Service stopped."
        ;;
    restart)
        echo "Restarting CF Agent AIV2 bot service..."
        launchctl unload "$PLIST_PATH"
        sleep 2
        launchctl load "$PLIST_PATH"
        echo "Service restarted."
        ;;
    status)
        echo "Checking status of CF Agent AIV2 bot service..."
        if launchctl list | grep -q "$SERVICE_NAME"; then
            echo "Service is running."
            launchctl list | grep "$SERVICE_NAME"
        else
            echo "Service is not running."
        fi
        ;;
    logs)
        echo "Displaying recent logs for CF Agent AIV2 bot service..."
        if [ -f "/Users/anthonypium/clawd/logs/bot.stdout.log" ]; then
            echo "STDOUT:"
            tail -20 "/Users/anthonypium/clawd/logs/bot.stdout.log"
        else
            echo "STDOUT log file does not exist yet at: /Users/anthonypium/clawd/logs/bot.stdout.log"
        fi
        if [ -f "/Users/anthonypium/clawd/logs/bot.stderr.log" ]; then
            echo "STDERR:"
            tail -20 "/Users/anthonypium/clawd/logs/bot.stderr.log"
        else
            echo "STDERR log file does not exist yet at: /Users/anthonypium/clawd/logs/bot.stderr.log"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac