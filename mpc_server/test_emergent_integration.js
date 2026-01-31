const axios = require('axios');

async function testServer() {
  try {
    console.log('Testing MPC Server Integration...');
    
    // Test health endpoint
    const healthResponse = await axios.get('http://localhost:3000/api/health');
    console.log('✓ Health check passed:', healthResponse.data);
    
    // Test root endpoint
    const rootResponse = await axios.get('http://localhost:3000/');
    console.log('✓ Root endpoint check passed:', rootResponse.data);
    
    console.log('\\nAll tests passed! Server is ready for Emergent AI integration.');
  } catch (error) {
    console.error('✗ Test failed:', error.message);
  }
}

// Only run if this file is executed directly
if (require.main === module) {
  testServer();
}

module.exports = testServer;