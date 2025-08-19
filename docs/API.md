# DockerFlow API Documentation

DockerFlow provides a comprehensive REST API for programmatic access to Claude-Flow functionality. The API includes OpenAPI documentation available at http://localhost:5002/docs when running.

## Base URL

When running locally: `http://localhost:5002`

## Authentication

Currently, API access is unrestricted when running locally. In production deployments, consider implementing authentication mechanisms.

## Core Endpoints

### Health Check

#### GET /health
Returns the health status of all services.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "api": "healthy",
    "websocket": "healthy",
    "terminal": "healthy",
    "claude_flow": "healthy"
  },
  "timestamp": "2024-08-19T12:00:00Z",
  "version": "1.0.0"
}
```

#### GET /status
Returns detailed system status and metrics.

**Response:**
```json
{
  "status": "running",
  "uptime": 3600,
  "memory_usage": {
    "total": "8GB",
    "used": "2GB",
    "available": "6GB"
  },
  "cpu_usage": "15%",
  "active_connections": 3,
  "claude_flow_version": "2.0.0-alpha.43"
}
```

### Command Execution

#### POST /run
Execute a command in the DockerFlow environment.

**Request Body:**
```json
{
  "cmd": "npx claude-flow --version",
  "timeout": 30,
  "working_dir": "/workspace"
}
```

**Response:**
```json
{
  "success": true,
  "stdout": "claude-flow version 2.0.0-alpha.43",
  "stderr": "",
  "exit_code": 0,
  "execution_time": 1.23,
  "timestamp": "2024-08-19T12:00:00Z"
}
```

#### POST /run/async
Execute a command asynchronously and return a job ID.

**Request Body:**
```json
{
  "cmd": "npx claude-flow sparc run architect \"design auth system\"",
  "timeout": 300,
  "working_dir": "/workspace"
}
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "running",
  "started_at": "2024-08-19T12:00:00Z"
}
```

#### GET /jobs/{job_id}
Get the status and results of an async job.

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "result": {
    "success": true,
    "stdout": "Architecture design completed...",
    "stderr": "",
    "exit_code": 0
  },
  "started_at": "2024-08-19T12:00:00Z",
  "completed_at": "2024-08-19T12:02:30Z"
}
```

### File Operations

#### GET /files
List files in the workspace.

**Query Parameters:**
- `path` (optional): Directory path (default: "/workspace")
- `recursive` (optional): Include subdirectories (default: false)

**Response:**
```json
{
  "path": "/workspace",
  "files": [
    {
      "name": "project1",
      "type": "directory",
      "size": null,
      "modified": "2024-08-19T11:30:00Z"
    },
    {
      "name": "README.md",
      "type": "file",
      "size": 1024,
      "modified": "2024-08-19T11:25:00Z"
    }
  ]
}
```

#### GET /files/content
Read file content.

**Query Parameters:**
- `path` (required): File path

**Response:**
```json
{
  "path": "/workspace/README.md",
  "content": "# My Project\n\nThis is my project...",
  "encoding": "utf-8",
  "size": 1024
}
```

#### POST /files/upload
Upload a file to the workspace.

**Request:** Multipart form data with file

**Response:**
```json
{
  "success": true,
  "path": "/workspace/uploaded_file.txt",
  "size": 2048
}
```

### Environment Management

#### GET /env
Get environment variables (non-sensitive ones).

**Response:**
```json
{
  "NODE_ENV": "production",
  "PYTHON_VERSION": "3.11",
  "NODE_VERSION": "20"
}
```

#### POST /env
Set environment variables for the session.

**Request Body:**
```json
{
  "variables": {
    "MY_VAR": "value",
    "DEBUG": "true"
  }
}
```

**Response:**
```json
{
  "success": true,
  "updated": ["MY_VAR", "DEBUG"]
}
```

## WebSocket API

Connect to `ws://localhost:5001/ws` for real-time communication.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:5001/ws');

ws.onopen = () => {
  console.log('Connected to DockerFlow WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Message Types

#### Execute Command
```json
{
  "type": "execute",
  "data": {
    "cmd": "npx claude-flow --version",
    "working_dir": "/workspace"
  }
}
```

#### Command Output
```json
{
  "type": "output",
  "data": {
    "stdout": "claude-flow version 2.0.0-alpha.43\n",
    "stderr": "",
    "finished": true,
    "exit_code": 0
  }
}
```

#### Status Update
```json
{
  "type": "status",
  "data": {
    "message": "Command completed",
    "timestamp": "2024-08-19T12:00:00Z"
  }
}
```

## Error Handling

All API endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable

Error responses include details:

```json
{
  "error": {
    "code": "COMMAND_FAILED",
    "message": "Command execution failed",
    "details": "Command 'invalid-command' not found",
    "timestamp": "2024-08-19T12:00:00Z"
  }
}
```

## Rate Limiting

- Command execution: 10 requests per minute per IP
- File operations: 100 requests per minute per IP
- WebSocket connections: 5 concurrent connections per IP

## Examples

### Python Client
```python
import requests
import json

# Execute a command
response = requests.post('http://localhost:5002/run', 
    json={'cmd': 'npx claude-flow --version'})
result = response.json()
print(f"Output: {result['stdout']}")

# Check health
health = requests.get('http://localhost:5002/health')
print(f"Status: {health.json()['status']}")
```

### JavaScript Client
```javascript
// Execute command
const response = await fetch('http://localhost:5002/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ cmd: 'npx claude-flow --version' })
});

const result = await response.json();
console.log('Output:', result.stdout);

// WebSocket connection
const ws = new WebSocket('ws://localhost:5001/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'output') {
    console.log('Command output:', data.data.stdout);
  }
};
```

### cURL Examples
```bash
# Health check
curl http://localhost:5002/health

# Execute command
curl -X POST http://localhost:5002/run \
  -H "Content-Type: application/json" \
  -d '{"cmd": "npx claude-flow --version"}'

# List files
curl "http://localhost:5002/files?path=/workspace"

# Upload file
curl -X POST -F "file=@myfile.txt" \
  http://localhost:5002/files/upload
```

## OpenAPI Documentation

For complete API documentation including request/response schemas, visit:
http://localhost:5002/docs

The OpenAPI specification is also available at:
http://localhost:5002/openapi.json