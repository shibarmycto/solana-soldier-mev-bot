# Emergent AI MPC Integration

This MPC server is designed to work with the Emergent AI platform as shown in the configuration interface.

## Configuration for Emergent AI

To integrate with Emergent AI's "Configure New MPC" interface, use the following JSON configuration:

```json
{
  "mcpServers": {
    "mev-bot-mpc": {
      "command": "npx",
      "args": ["-y", "@clawd/mpc-server"],
      "env": {
        "API_KEY": "your-secret-api-key-here",
        "PORT": "3000",
        "NODE_ENV": "production",
        "CORS_ORIGIN": "*" 
      }
    }
  }
}
```

## Features

### Multi-Party Computation for MEV Operations
- Secure computation across multiple parties
- MEV strategy coordination (arbitrage, sandwich attacks, liquidations)
- Real-time opportunity detection and execution

### Sub-Agent System
- Automated coding assistance for smart contracts
- Task assignment and completion tracking
- Scalable worker architecture

### Security
- API key authentication for all endpoints
- Secure WebSocket connections
- Input validation and sanitization

## Deployment

### Option 1: Direct npm package
```bash
npx -y @clawd/mpc-server
```

### Option 2: Local development
```bash
git clone <repository>
cd mpc_server
npm install
npm start
```

### Environment Variables
- `API_KEY`: Authentication key for the server (required)
- `PORT`: Port to run the server on (default: 3000)
- `NODE_ENV`: Environment mode (development/production)
- `CORS_ORIGIN`: Allowed origin for CORS (default: "*")

## API Endpoints

### HTTP Endpoints
- `GET /` - Server status
- `GET /api/health` - Health check

### WebSocket Events
- `init_session` - Initialize MPC session
- `join_session` - Join existing session
- `submit_input` - Submit input for MPC
- `execute_mev_strategy` - Execute MEV strategy
- `register_sub_agent` - Register coding sub-agent
- `request_coding_task` - Request coding assistance

## Integration with Emergent AI Platform

The server is designed to be launched via npx as specified in the Emergent configuration. When deployed through the Emergent platform:

1. The platform will execute: `npx -y @clawd/mpc-server`
2. Environment variables will be injected as specified in the config
3. The server will start and listen for MPC connections
4. Sub-agents can register and handle coding tasks
5. MEV strategies can be executed securely across multiple parties

## Example Usage

```javascript
// Connect to the MPC server
const socket = io('ws://your-server:3000', {
  auth: { api_key: 'your-secret-api-key-here' }
});

// Initialize an MPC session for MEV strategy
socket.emit('init_session', {
  computation: 'mev-arbitrage-strategy'
});

// Submit private inputs for computation
socket.emit('submit_input', {
  sessionId: 'session-id-from-init',
  input: { privateData: '...' }
});
```