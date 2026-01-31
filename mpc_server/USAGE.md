# MPC Server for MEV Bot Operations - Usage Guide

## Overview

This MPC (Multi-Party Computation) server is specifically designed for MEV (Maximal Extractable Value) bot operations with integrated sub-agent capabilities for automated coding tasks. The server is compatible with the Emergent AI platform.

## Quick Start

### Running with npx (for Emergent AI integration)
```bash
npx -y @clawd/mpc-server
```

### Running locally
```bash
# Clone and install
git clone <repository>
cd mpc_server
npm install

# Set up environment
cp .env.example .env
# Edit .env with your API key

# Start server
npm start
```

## Configuration for Emergent AI Platform

Use this JSON configuration in the Emergent AI "Configure New MPC" interface:

```json
{
  "mcpServers": {
    "mev-bot-mpc": {
      "command": "npx",
      "args": ["-y", "@clawd/mpc-server"],
      "env": {
        "API_KEY": "your-secret-api-key-here",
        "PORT": "3000",
        "NODE_ENV": "production"
      }
    }
  }
}
```

## API Endpoints

### HTTP Endpoints
- `GET /` - Server status information
- `GET /api/health` - Health check with uptime information

### WebSocket Events
The server uses Socket.IO for real-time communication:

#### MPC Operations
- `init_session` - Initialize a new MPC session
  ```javascript
  socket.emit('init_session', { computation: 'mev-arbitrage-strategy' });
  // Response: { sessionId, message }
  ```

- `join_session` - Join an existing session
  ```javascript
  socket.emit('join_session', { sessionId: 'session-id' });
  // Response: { sessionId, totalParties }
  ```

- `submit_input` - Submit private input for MPC
  ```javascript
  socket.emit('submit_input', {
    sessionId: 'session-id',
    input: { privateData: '...' },
    partyId: 'unique-party-id'
  });
  ```

#### MEV Operations
- `execute_mev_strategy` - Execute MEV strategy using MPC
  ```javascript
  socket.emit('execute_mev_strategy', {
    strategy: 'arbitrage', // 'arbitrage', 'sandwich', 'liquidation'
    params: { exchanges: ['Uniswap', 'Sushiswap'] }
  });
  // Response: { success, result, strategy, timestamp }
  ```

#### Sub-Agent Operations
- `register_sub_agent` - Register a coding sub-agent
  ```javascript
  socket.emit('register_sub_agent', { agentId: 'agent-unique-id' });
  // Response: { success, agentId }
  ```

- `request_coding_task` - Request coding assistance
  ```javascript
  socket.emit('request_coding_task', {
    taskId: 'task-id',
    requirements: 'Create a smart contract for...',
    priority: 'normal'
  });
  // Response: { taskId, result } (via 'coding_task_result' event)
  ```

## Environment Variables

- `API_KEY` (required): Authentication key for the server
- `PORT`: Port to run the server on (default: 3000)
- `NODE_ENV`: Environment mode (development/production)
- `CORS_ORIGIN`: Allowed origin for CORS (default: "*")

## MEV Strategies Supported

The server supports several MEV strategies:

1. **Arbitrage**: Cross-exchange arbitrage opportunities
2. **Sandwich Attacks**: Front-run and back-run large trades
3. **Liquidations**: Identify and execute liquidation opportunities
4. **Custom Strategies**: User-defined MEV strategies

## Sub-Agent System

The integrated sub-agent system allows for automated coding tasks:
- Smart contract development
- Transaction simulation
- Strategy implementation
- Code optimization

## Security Features

- API key authentication for all endpoints
- Secure WebSocket connections
- Input validation and sanitization
- Session-based access controls
- Rate limiting protection

## Example Usage

```javascript
const io = require('socket.io-client');

// Connect to server
const socket = io('http://localhost:3000', {
  auth: { api_key: 'your-api-key' }
});

socket.on('connect', () => {
  console.log('Connected to MPC server');
  
  // Initialize MEV strategy session
  socket.emit('init_session', {
    computation: 'mev-arbitrage-strategy'
  });
});

socket.on('session_ready', (data) => {
  console.log('MPC session ready:', data.sessionId);
  
  // Submit private market data
  socket.emit('submit_input', {
    sessionId: data.sessionId,
    input: { marketData: {...} }
  });
});

socket.on('computation_complete', (data) => {
  console.log('MPC computation complete:', data.result);
  
  // Execute identified MEV opportunity
  socket.emit('execute_mev_strategy', {
    strategy: 'arbitrage',
    params: data.result
  });
});
```

## Integration with Emergent AI

The server is designed to be deployed through the Emergent AI platform:
1. Package is published to npm as `@clawd/mpc-server`
2. Launched via npx with provided configuration
3. Environment variables injected at runtime
4. Automatic scaling and management by Emergent platform