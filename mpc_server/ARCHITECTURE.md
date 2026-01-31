# MPC Server Architecture

## Overview

The MPC (Multi-Party Computation) Server with Sub-Agent System provides a secure platform for collaborative computation and automated coding assistance.

## Components

### 1. Main Server (`server.js`)
- Handles WebSocket connections for real-time communication
- Manages MPC session lifecycle
- Coordinates between multiple parties in MPC protocols
- Routes coding tasks to available sub-agents
- Ensures secure communication between parties

### 2. Sub-Agent System (`sub_agent.js`)
- Connects to the main server as a specialized worker
- Listens for coding task assignments
- Processes requirements and generates appropriate code
- Returns results to the requesting party
- Maintains availability status

### 3. Client Interface (`client_example.js`)
- Provides methods to interact with the MPC server
- Handles session creation and management
- Submits inputs for MPC computations
- Requests coding assistance from sub-agents

## Features

### Multi-Party Computation
- Session-based computation coordination
- Input submission from multiple parties
- Secure computation result distribution
- Party management and tracking

### Automated Coding Assistance
- Task assignment to sub-agents
- Requirement-based code generation
- Real-time task completion notifications
- Error handling for failed tasks

### Security Considerations
- Session-based authentication
- Encrypted communication channels
- Input validation and sanitization
- Isolated task execution environment

## Usage

### Starting the Server
```bash
npm start
```

### Running a Sub-Agent
```bash
node run_sub_agent.js
```

### Using the Client
```javascript
const client = new MPCClClient('http://localhost:3000');
client.connect();

// Request coding assistance
client.requestCodingTask('Create a function to sort an array');

// Initialize MPC session
client.initMPC('addition');

// Submit input for MPC
client.submitInput(sessionId, inputData);
```

## Future Enhancements

- Enhanced cryptographic protocols for true MPC
- Advanced code generation with AI integration
- Load balancing for multiple sub-agents
- Persistent session storage
- Enhanced security measures
- Performance optimization