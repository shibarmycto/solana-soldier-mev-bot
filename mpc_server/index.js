#!/usr/bin/env node

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
require('dotenv').config();

// Initialize Express app
const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: process.env.CORS_ORIGIN || "*",
    methods: ["GET", "POST"]
  }
});

// Middleware
app.use(cors());
app.use(express.json());

// Get port from environment or default to 3000
const PORT = process.env.PORT || 3000;
const API_KEY = process.env.API_KEY;

// Authentication middleware
const authenticate = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const apiKey = authHeader && authHeader.replace('Bearer ', '');
  
  if (!apiKey || apiKey !== API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  next();
};

// Store active MPC sessions
const sessions = new Map();

// API routes
app.get('/', (req, res) => {
  res.json({ 
    message: 'MPC Server for MEV Bot Operations',
    status: 'running',
    version: '1.0.0'
  });
});

app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  });
});

// Socket.IO connection handling
io.use((socket, next) => {
  const apiKey = socket.handshake.auth.api_key;
  if (apiKey === API_KEY) {
    next();
  } else {
    next(new Error('Authentication error'));
  }
});

io.on('connection', (socket) => {
  console.log(`MPC client connected: ${socket.id}`);

  // Handle MPC session initialization
  socket.on('init_session', (data) => {
    const sessionId = require('crypto').randomBytes(16).toString('hex');
    
    const session = {
      id: sessionId,
      parties: [socket.id],
      computation: data.computation || 'default',
      inputs: {},
      results: null,
      createdAt: new Date()
    };
    
    sessions.set(sessionId, session);
    socket.join(sessionId);
    
    socket.emit('session_ready', { 
      sessionId, 
      message: 'MPC session initialized' 
    });
  });

  // Handle party joining existing session
  socket.on('join_session', (data) => {
    const { sessionId } = data;
    const session = sessions.get(sessionId);
    
    if (!session) {
      socket.emit('error', { message: 'Session not found' });
      return;
    }

    if (!session.parties.includes(socket.id)) {
      session.parties.push(socket.id);
    }
    
    socket.join(sessionId);
    socket.to(sessionId).emit('party_joined', { 
      partyId: socket.id, 
      totalParties: session.parties.length 
    });
    
    socket.emit('session_joined', { 
      sessionId, 
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

  // Handle MEV bot specific operations
  socket.on('execute_mev_strategy', async (data) => {
    const { strategy, params } = data;
    
    try {
      // Simulate MEV strategy execution using MPC
      const result = await executeMEVStrategy(strategy, params);
      
      socket.emit('mev_execution_result', {
        success: true,
        result,
        strategy,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      socket.emit('mev_execution_result', {
        success: false,
        error: error.message,
        strategy,
        timestamp: new Date().toISOString()
      });
    }
  });

  // Handle sub-agent registration for coding tasks
  socket.on('register_sub_agent', (data) => {
    console.log(`Sub-agent registered: ${data.agentId}`);
    socket.subAgentId = data.agentId;
    socket.isSubAgent = true;
    
    socket.emit('sub_agent_registered', { 
      success: true,
      agentId: data.agentId
    });
  });

  // Handle coding task requests
  socket.on('request_coding_task', async (data) => {
    const { taskId, requirements, priority = 'normal' } = data;
    
    // Find available sub-agents
    const availableAgents = Array.from(io.sockets.sockets.values())
      .filter(client => client.isSubAgent && client.connected);
    
    if (availableAgents.length === 0) {
      socket.emit('error', { message: 'No sub-agents available' });
      return;
    }

    // Assign task to an available sub-agent
    const agent = availableAgents[0];
    agent.emit('coding_task_assigned', { 
      taskId, 
      requirements, 
      priority,
      requester: socket.id 
    });
  });

  // Handle completion of coding tasks
  socket.on('coding_task_completed', (data) => {
    const { taskId, result, requesterId } = data;
    
    const requester = io.sockets.sockets.get(requesterId);
    if (requester) {
      requester.emit('coding_task_result', { taskId, result });
    }
  });

  socket.on('disconnect', () => {
    console.log(`MPC client disconnected: ${socket.id}`);
    
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
async function performComputation(sessionId) {
  const session = sessions.get(sessionId);
  if (!session) return;

  // In a real implementation, this would perform secure multi-party computation
  // For MEV bot operations, this could be calculating optimal arbitrage strategies
  // or coordinating private transactions among multiple parties
  
  // Simulate computation with a delay
  await new Promise(resolve => setTimeout(resolve, 100));
  
  // Example: aggregate inputs from all parties for MEV calculation
  let result = {};
  Object.entries(session.inputs).forEach(([partyId, input]) => {
    // Process each party's input in the MPC computation
    if (typeof input === 'object') {
      Object.assign(result, input);
    }
  });

  session.results = result;

  // Broadcast result to all parties in the session
  io.to(sessionId).emit('computation_complete', { 
    result,
    sessionId
  });
}

// Execute MEV strategy using MPC
async function executeMEVStrategy(strategy, params) {
  // Simulate executing an MEV strategy using MPC
  // This would normally involve complex calculations across multiple parties
  // to find optimal transaction ordering, arbitrage opportunities, etc.
  
  switch (strategy) {
    case 'arbitrage':
      return {
        opportunity: 'Cross-exchange arbitrage detected',
        profitEstimate: Math.random() * 1000 + 100, // Random estimate
        exchanges: params.exchanges || ['Uniswap', 'Sushiswap'],
        tokens: params.tokens || ['WETH', 'USDC']
      };
    
    case 'sandwich':
      return {
        opportunity: 'Sandwich attack opportunity',
        profitEstimate: Math.random() * 500 + 50,
        targetTx: params.targetTx || '0x...',
        deadline: params.deadline || Date.now() + 30000
      };
    
    case 'liquidation':
      return {
        opportunity: 'Liquidation opportunity',
        profitEstimate: Math.random() * 2000 + 200,
        positions: params.positions || ['AAVE', 'Compound'],
        collateral: params.collateral || 'ETH'
      };
    
    default:
      return {
        opportunity: `Custom strategy: ${strategy}`,
        params,
        estimatedProfit: Math.random() * 500 + 50
      };
  }
}

// Start the server
server.listen(PORT, () => {
  console.log(`MPC Server for MEV Bot Operations running on port ${PORT}`);
  console.log(`API Key: ${API_KEY ? 'Loaded' : 'Not set (check environment)'}`);
  console.log('Ready to accept MPC connections...');
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down MPC server...');
  server.close(() => {
    console.log('MPC server closed.');
    process.exit(0);
  });
});

module.exports = { app, server, io };