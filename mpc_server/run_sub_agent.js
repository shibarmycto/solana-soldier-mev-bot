const CodingSubAgent = require('./sub_agent');

// Create and run a sub-agent
const agent = new CodingSubAgent('http://localhost:3000', 'coding-agent-001');

console.log('Starting coding sub-agent...');
agent.connect();

// Keep the process alive
process.on('SIGINT', () => {
  console.log('\\nShutting down sub-agent...');
  agent.disconnect();
  process.exit(0);
});