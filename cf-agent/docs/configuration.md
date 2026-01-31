# Example Configuration

## Environment Variables
The following environment variables should be configured for the CF Agent:

- `DEBUG`: Enable/disable debugging (true/false)
- `API_KEY`: Authentication key for protected endpoints
- `DATABASE_URL`: Connection string for external databases (if needed)

## Cloudflare Specific Configuration
In your `wrangler.toml`, ensure you have:

- KV namespaces for caching
- D1 database bindings for structured data
- R2 bucket bindings for file storage
- AI bindings for machine learning features