const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const crypto = require('crypto');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Middleware for authentication
const authenticate = (socket, next) => {
  // In a real implementation, verify credentials here
  console.log(`Connection attempt from ${socket.handshake.address}`);
  next();
};

io.use(authenticate);

// Store active sessions
const sessions = new Map();

io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);

  // Handle MPC protocol initialization
  socket.on('init_mpc', (data) => {
    const sessionId = crypto.randomBytes(16).toString('hex');
    
    sessions.set(sessionId, {
      parties: [socket.id],
      computation: data.computation,
      inputs: {},
      results: null
    });
    
    socket.join(sessionId);
    
    socket.emit('session_created', { sessionId });
  });

  // Handle party joining an existing session
  socket.on('join_session', (data) => {
    const { sessionId } = data;
    const session = sessions.get(sessionId);
    
    if (!session) {
      socket.emit('error', { message: 'Session not found' });
      return;
    }

    // Add this client to the session
    if (!session.parties.includes(socket.id)) {
      session.parties.push(socket.id);
    }
    
    socket.join(sessionId);
    socket.to(sessionId).emit('party_joined', { 
      partyId: socket.id, 
      totalParties: session.parties.length 
    });
  });

  // Handle input submission for MPC
  socket.on('submit_input', (data) => {
    const { sessionId, input, partyId } = data;
    const session = sessions.get(sessionId);
    
    if (!session) {
      socket.emit('error', { message: 'Session not found' });
      return;
    }

    // Store encrypted input
    session.inputs[partyId || socket.id] = input;

    // Check if all parties have submitted input
    if (Object.keys(session.inputs).length === session.parties.length) {
      // Perform computation
      performComputation(sessionId);
    }
  });

  // Handle sub-agent connection
  socket.on('register_sub_agent', (data) => {
    console.log(`Sub-agent registered: ${data.agentId}`);
    socket.subAgentId = data.agentId;
    socket.emit('sub_agent_registered', { success: true });
  });

  // Handle coding task requests
  socket.on('request_coding_task', async (data) => {
    const { taskId, requirements } = data;
    
    // Find available sub-agent
    const subAgents = Array.from(io.sockets.sockets.values())
      .filter(client => client.subAgentId);
    
    if (subAgents.length === 0) {
      socket.emit('error', { message: 'No sub-agents available' });
      return;
    }

    // Assign task to first available sub-agent
    const agent = subAgents[0];
    agent.emit('coding_task_assigned', { taskId, requirements, requester: socket.id });
  });

  // Handle completion of coding task
  socket.on('coding_task_completed', (data) => {
    const { taskId, result, requesterId } = data;
    
    // Send result back to requester
    const requester = io.sockets.sockets.get(requesterId);
    if (requester) {
      requester.emit('coding_task_result', { taskId, result });
    }
  });

  socket.on('disconnect', () => {
    console.log(`Client disconnected: ${socket.id}`);
    
    // Clean up sessions associated with this socket
    sessions.forEach((session, sessionId) => {
      const index = session.parties.indexOf(socket.id);
      if (index > -1) {
        session.parties.splice(index, 1);
        
        if (session.parties.length === 0) {
          sessions.delete(sessionId);
        }
      }
    });
  });
});

// Perform MPC computation
function performComputation(sessionId) {
  const session = sessions.get(sessionId);
  if (!session) return;

  // In a real implementation, this would perform secure multi-party computation
  // For now, we'll simulate the computation
  
  // Example: sum of inputs from all parties
  let result = 0;
  Object.values(session.inputs).forEach(input => {
    if (typeof input === 'number') {
      result += input;
    }
  });

  session.results = result;

  // Broadcast result to all parties in the session
  io.to(sessionId).emit('computation_complete', { result });
}

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`MPC Server listening on port ${PORT}`);
});