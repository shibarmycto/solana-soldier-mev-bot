const MPCClClient = require('./client_example');

// Create a test client
const client = new MPCClClient('http://localhost:3000');

client.connect();

// Wait for connection then run tests
setTimeout(() => {
  console.log('\\n--- Testing MPC Server Functionality ---');
  
  // Test 1: Request a coding task
  console.log('\\n1. Requesting coding task...');
  client.requestCodingTask('Create a JavaScript function that calculates factorial of a number recursively');
  
  // Test 2: Initialize MPC session
  console.log('\\n2. Initializing MPC session for addition...');
  client.initMPC('addition');
  
  // Test 3: Another coding task
  setTimeout(() => {
    console.log('\\n3. Requesting another coding task...');
    client.requestCodingTask('Create a simple Express.js API endpoint that returns current timestamp');
  }, 3000);
  
}, 1000);

// Keep the process alive for testing
setTimeout(() => {
  console.log('\\nTest completed. Disconnecting...');
  client.disconnect();
  process.exit(0);
}, 10000);