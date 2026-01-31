const socket = require('socket.io-client');

class MPCClClient {
  constructor(serverUrl) {
    this.serverUrl = serverUrl;
    this.socket = null;
  }

  connect() {
    this.socket = socket(this.serverUrl);
    
    this.socket.on('connect', () => {
      console.log('Connected to MPC server');
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from MPC server');
    });

    // Handle session creation
    this.socket.on('session_created', (data) => {
      console.log('MPC session created:', data.sessionId);
      this.handleSessionCreated(data.sessionId);
    });

    // Handle party joining
    this.socket.on('party_joined', (data) => {
      console.log(`Party joined session. Total parties: ${data.totalParties}`);
    });

    // Handle computation completion
    this.socket.on('computation_complete', (data) => {
      console.log('Computation completed:', data.result);
      this.handleComputationResult(data.result);
    });

    // Handle coding task results
    this.socket.on('coding_task_result', (data) => {
      console.log(`Coding task ${data.taskId} completed:`);
      console.log(data.result);
    });

    // Handle errors
    this.socket.on('error', (error) => {
      console.error('Client error:', error);
    });
  }

  // Initialize an MPC session
  initMPC(computation) {
    this.socket.emit('init_mpc', {
      computation: computation
    });
  }

  // Join an existing MPC session
  joinSession(sessionId) {
    this.socket.emit('join_session', {
      sessionId: sessionId
    });
  }

  // Submit input for MPC
  submitInput(sessionId, input) {
    this.socket.emit('submit_input', {
      sessionId: sessionId,
      input: input,
      partyId: this.socket.id
    });
  }

  // Request a coding task to be performed by a sub-agent
  requestCodingTask(requirements) {
    const taskId = `task_${Date.now()}`;
    
    this.socket.emit('request_coding_task', {
      taskId: taskId,
      requirements: requirements
    });
    
    console.log(`Requested coding task: ${taskId} with requirements: ${requirements}`);
  }

  handleSessionCreated(sessionId) {
    // Override this method in subclass to implement custom logic
    console.log(`Session ${sessionId} is ready for inputs`);
  }

  handleComputationResult(result) {
    // Override this method in subclass to implement custom logic
    console.log('Received computation result:', result);
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}

// Example usage
if (require.main === module) {
  const client = new MPCClClient('http://localhost:3000');
  
  client.connect();
  
  // Wait for connection
  setTimeout(() => {
    // Example 1: Initialize an MPC session for addition
    console.log('\\n--- Starting MPC Addition Example ---');
    client.initMPC('addition');
    
    // Example 2: Request a coding task
    console.log('\\n--- Requesting Coding Task ---');
    client.requestCodingTask('Create a simple calculator class with add, subtract, multiply, divide methods');
  }, 1000);
}

module.exports = MPCClClient;