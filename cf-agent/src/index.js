// Matrix AI Agent - Cloudflare Worker
// Integrates Agent Zero framework and Clawdbot system

export default {
  /**
   * Handles incoming requests to the Matrix AI Agent
   */
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    try {
      // CORS headers
      const corsHeaders = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Max-Age": "86400"
      };

      // Handle preflight requests
      if (method === "OPTIONS") {
        return new Response(null, { headers: corsHeaders });
      }

      // Add CORS headers to all responses
      const addCors = (response) => {
        response.headers.set("Access-Control-Allow-Origin", "*");
        return response;
      };

      // Route based on path
      switch (path) {
        case "/":
        case "/health":
          return addCors(this.handleHealth());
        
        case "/api/agent-zero":
        case "/api/agents":
          return addCors(await this.handleAgentZero(request, env));
        
        case "/api/clawd":
        case "/api/clawdbot":
          return addCors(await this.handleClawd(request, env));
        
        case "/api/links":
        case "/api/tunnels":
          return addCors(await this.handleLinks(request, env));
        
        case "/api/status":
          return addCors(await this.handleStatus(env));
        
        case "/api/webhook":
          return addCors(await this.handleWebhook(request, env));
        
        default:
          // Serve static assets or return 404
          if (path.startsWith("/assets/") || path.endsWith(".js") || path.endsWith(".css")) {
            return addCors(this.serveStatic(path, env));
          } else {
            return addCors(this.handleNotFound());
          }
      }
    } catch (error) {
      console.error("Request error:", error);
      return addCors(new Response(JSON.stringify({ 
        error: "Internal Server Error",
        message: error.message 
      }), { 
        status: 500,
        headers: { "Content-Type": "application/json" }
      }));
    }
  },

  /**
   * Health check endpoint
   */
  handleHealth() {
    return new Response(JSON.stringify({
      status: "healthy",
      service: "Matrix AI Agent",
      timestamp: new Date().toISOString(),
      uptime: "24/7",
      features: ["Agent Zero", "Clawdbot", "Cloudflare Integration"]
    }), {
      headers: { "Content-Type": "application/json" }
    });
  },

  /**
   * Handle Agent Zero framework requests
   */
  async handleAgentZero(request, env) {
    const method = request.method;
    
    if (method === "POST") {
      const body = await request.json();
      
      // Process Agent Zero request
      const agentResponse = await this.processAgentZeroRequest(body, env);
      
      return new Response(JSON.stringify(agentResponse), {
        headers: { "Content-Type": "application/json" }
      });
    } else if (method === "GET") {
      // Return Agent Zero status
      const status = {
        framework: "Agent Zero",
        status: "active",
        capabilities: ["multi-agent", "cooperation", "task-execution"],
        timestamp: new Date().toISOString()
      };
      
      return new Response(JSON.stringify(status), {
        headers: { "Content-Type": "application/json" }
      });
    } else {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json" }
      });
    }
  },

  /**
   * Handle Clawdbot system requests
   */
  async handleClawd(request, env) {
    const method = request.method;
    
    if (method === "POST") {
      const body = await request.json();
      
      // Process Clawdbot request
      const clawdResponse = await this.processClawdRequest(body, env);
      
      return new Response(JSON.stringify(clawdResponse), {
        headers: { "Content-Type": "application/json" }
      });
    } else if (method === "GET") {
      // Return Clawdbot status
      const status = {
        framework: "Clawdbot",
        status: "active",
        capabilities: ["ai-assistant", "gateway", "integration"],
        timestamp: new Date().toISOString()
      };
      
      return new Response(JSON.stringify(status), {
        headers: { "Content-Type": "application/json" }
      });
    } else {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json" }
      });
    }
  },

  /**
   * Handle persistent link generation
   */
  async handleLinks(request, env) {
    const method = request.method;
    
    if (method === "POST") {
      const body = await request.json();
      
      // Generate persistent link
      const linkData = await this.generatePersistentLink(body, env);
      
      return new Response(JSON.stringify(linkData), {
        headers: { "Content-Type": "application/json" }
      });
    } else if (method === "GET") {
      // Return active links
      const activeLinks = await this.getActiveLinks(env);
      
      return new Response(JSON.stringify(activeLinks), {
        headers: { "Content-Type": "application/json" }
      });
    } else {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json" }
      });
    }
  },

  /**
   * Handle system status
   */
  async handleStatus(env) {
    // Get system metrics from D1 and KV
    const dbStatus = await this.checkDatabaseStatus(env);
    const kvStatus = await this.checkKVStatus(env);
    
    const status = {
      service: "Matrix AI Agent",
      status: "operational",
      timestamp: new Date().toISOString(),
      databases: dbStatus,
      storage: kvStatus,
      uptime: "24/7",
      global: true,
      cdn: "active"
    };
    
    return new Response(JSON.stringify(status), {
      headers: { "Content-Type": "application/json" }
    });
  },

  /**
   * Handle webhook requests
   */
  async handleWebhook(request, env) {
    const method = request.method;
    
    if (method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json" }
      });
    }
    
    const body = await request.json();
    
    // Process webhook
    const result = await this.processWebhook(body, env);
    
    return new Response(JSON.stringify(result), {
      headers: { "Content-Type": "application/json" }
    });
  },

  /**
   * Process Agent Zero request
   */
  async processAgentZeroRequest(data, env) {
    // Simulate Agent Zero processing
    // In a real implementation, this would call the actual Agent Zero framework
    return {
      success: true,
      agentId: this.generateId(),
      task: data.task || "default",
      status: "processed",
      result: "Agent Zero framework executed successfully",
      timestamp: new Date().toISOString(),
      processedBy: "Cloudflare Worker"
    };
  },

  /**
   * Process Clawdbot request
   */
  async processClawdRequest(data, env) {
    // Simulate Clawdbot processing
    // In a real implementation, this would call the actual Clawdbot system
    return {
      success: true,
      requestId: this.generateId(),
      command: data.command || "status",
      status: "executed",
      result: "Clawdbot system processed request",
      timestamp: new Date().toISOString(),
      processedBy: "Cloudflare Worker"
    };
  },

  /**
   * Generate persistent link
   */
  async generatePersistentLink(data, env) {
    const linkId = this.generateId();
    const domain = `${linkId}.matrix-ai-agent.your-subdomain.workers.dev`;
    
    // Store link in KV for persistence
    const linkData = {
      id: linkId,
      domain: domain,
      created: new Date().toISOString(),
      expires: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // 24 hours
      active: true,
      visits: 0,
      config: data.config || {}
    };
    
    // Store in KV with expiration
    await env.KV.put(`link:${linkId}`, JSON.stringify(linkData), {
      expirationTtl: 24 * 60 * 60 // 24 hours in seconds
    });
    
    return {
      success: true,
      linkId: linkId,
      domain: `https://${domain}`,
      status: "created",
      expires: linkData.expires,
      timestamp: new Date().toISOString()
    };
  },

  /**
   * Get active links
   */
  async getActiveLinks(env) {
    // In a real implementation, we would scan KV for active links
    // For now, return a sample
    return {
      count: 0,
      links: [],
      timestamp: new Date().toISOString()
    };
  },

  /**
   * Process webhook
   */
  async processWebhook(data, env) {
    // Process incoming webhook
    return {
      success: true,
      received: new Date().toISOString(),
      processed: true,
      data: data,
      message: "Webhook processed successfully"
    };
  },

  /**
   * Check database status
   */
  async checkDatabaseStatus(env) {
    try {
      // Test D1 connection
      const results = await env.DB.prepare("SELECT 1 as test").all();
      return {
        status: "connected",
        available: true,
        testResult: results
      };
    } catch (error) {
      return {
        status: "disconnected",
        available: false,
        error: error.message
      };
    }
  },

  /**
   * Check KV status
   */
  async checkKVStatus(env) {
    try {
      // Test KV connection
      const testKey = `healthcheck:${Date.now()}`;
      await env.KV.put(testKey, "healthy", { expirationTtl: 60 });
      const value = await env.KV.get(testKey);
      
      return {
        status: "connected",
        available: true,
        testValue: value
      };
    } catch (error) {
      return {
        status: "disconnected",
        available: false,
        error: error.message
      };
    }
  },

  /**
   * Serve static assets
   */
  async serveStatic(path, env) {
    // Return 404 for static assets in this basic implementation
    return new Response("Not Found", { status: 404 });
  },

  /**
   * Handle 404
   */
  handleNotFound() {
    return new Response(JSON.stringify({ 
      error: "Not Found", 
      message: "The requested resource was not found" 
    }), { 
      status: 404,
      headers: { "Content-Type": "application/json" }
    });
  },

  /**
   * Generate random ID
   */
  generateId() {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  }
};
