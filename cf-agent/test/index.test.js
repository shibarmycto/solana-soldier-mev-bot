# CF Agent Test Suite

const { createExecutionContext, env, SELF } = require('cloudflare:test');
const { default: worker } = require('../src/index');

// Mock test for the worker
describe('CF Agent Worker', () => {
  test('GET / returns expected response', async () => {
    const request = new Request('http://example.com/', { method: 'GET' });
    const response = await worker.fetch(request, env, createExecutionContext());
    
    expect(response.status).toBe(200);
    const text = await response.text();
    expect(text).toContain('CF Agent is running!');
  });

  test('GET /health returns healthy status', async () => {
    const request = new Request('http://example.com/health', { method: 'GET' });
    const response = await worker.fetch(request, env, createExecutionContext());
    
    expect(response.status).toBe(200);
    const json = await response.json();
    expect(json.status).toBe('healthy');
  });

  test('POST /api/webhook processes webhook', async () => {
    const request = new Request('http://example.com/api/webhook', {
      method: 'POST',
      body: JSON.stringify({ test: 'data' }),
      headers: { 'Content-Type': 'application/json' }
    });
    const response = await worker.fetch(request, env, createExecutionContext());
    
    expect(response.status).toBe(200);
    const json = await response.json();
    expect(json.success).toBe(true);
  });
});