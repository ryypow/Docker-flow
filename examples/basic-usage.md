# DockerFlow Basic Usage Examples

This guide provides practical examples of using DockerFlow for various development scenarios.

## Getting Started

### 1. Quick Setup

```bash
# Clone the repository
git clone https://github.com/your-username/dockerflow.git
cd dockerflow

# Setup and configure
./scripts/setup.sh

# Edit .env with your API keys
nano .env

# Start DockerFlow
docker compose up -d
```

### 2. Accessing Services

- **Web UI**: http://localhost:5000
- **Terminal**: http://localhost:7681
- **API**: http://localhost:5002
- **WebSocket**: ws://localhost:5001

## Common Workflows

### Running Claude-Flow Commands

#### Via Web UI
1. Open http://localhost:5000
2. Use the command buttons or terminal
3. View real-time output

#### Via Container Shell
```bash
# Access the container
docker exec -it dockerflow bash

# Check Claude-Flow version
npx claude-flow --version

# Initialize a swarm
npx claude-flow swarm init mesh

# Run SPARC workflow
npx claude-flow sparc run architect "design a REST API"
```

#### Via API
```bash
# Check status
curl http://localhost:5002/status

# Run a command
curl -X POST http://localhost:5002/run \
  -H "Content-Type: application/json" \
  -d '{"cmd": "npx claude-flow --version"}'

# Stream output via WebSocket
# Use your preferred WebSocket client
websocat ws://localhost:5001/ws
```

### Working with Projects

#### Adding Your Project
```bash
# Clone your project into workspace
git clone https://github.com/your-repo workspace/my-project

# Access it in the container
docker exec -it dockerflow bash
cd /workspace/my-project

# Run Claude-Flow commands on your project
npx claude-flow scan
npx claude-flow sparc tdd "user authentication"
```

#### Using Persistent Storage
```bash
# Your workspace persists between container restarts
docker compose down
docker compose up -d

# Your files are still there
docker exec -it dockerflow ls /workspace
```

### Development Scenarios

#### Building a Web Application
```bash
# In the container terminal
cd /workspace
npx claude-flow sparc run architect "design a todo app with React and FastAPI"
npx claude-flow sparc tdd "user management system"
npx claude-flow sparc run integration "connect frontend to backend"
```

#### API Development
```bash
# Design API architecture
npx claude-flow sparc run architect "REST API for e-commerce"

# Implement with TDD
npx claude-flow sparc tdd "product catalog endpoints"
npx claude-flow sparc tdd "order management system"

# Document the API
npx claude-flow sparc run docs "API documentation"
```

#### Code Analysis and Refactoring
```bash
# Analyze existing code
npx claude-flow scan /workspace/my-project

# Get refactoring suggestions
npx claude-flow sparc run refactor "improve code quality"

# Performance optimization
npx claude-flow sparc run optimize "database queries"
```

## Advanced Usage

### Multi-Agent Coordination
```bash
# Initialize a mesh topology
npx claude-flow swarm init mesh

# Spawn specialized agents
npx claude-flow agent spawn researcher
npx claude-flow agent spawn coder
npx claude-flow agent spawn tester

# Orchestrate complex tasks
npx claude-flow task orchestrate "build microservices architecture"
```

### GPU-Accelerated Workflows
```bash
# Enable GPU support in docker-compose.yml
# Uncomment the deploy section

# Use GPU for intensive tasks
npx claude-flow neural train --use-gpu
npx claude-flow sparc run ml "train recommendation model"
```

### Monitoring and Debugging
```bash
# Check service status
curl http://localhost:5002/health

# View logs
docker compose logs -f

# Monitor resource usage
docker stats dockerflow

# Debug connectivity
docker exec -it dockerflow ping host.docker.internal
```

## Troubleshooting Common Issues

### Container Won't Start
```bash
# Check logs
docker compose logs

# Rebuild image
docker compose build --no-cache

# Reset everything
docker compose down -v
docker compose up -d
```

### API Key Issues
```bash
# Verify environment variables
docker exec -it dockerflow env | grep API_KEY

# Restart with new environment
docker compose down
docker compose up -d
```

### Performance Issues
```bash
# Increase resource limits in docker-compose.yml
# Check system resources
docker system df
docker system prune

# Monitor container resources
docker stats
```

### Network Issues
```bash
# Check port availability
netstat -tlnp | grep :5000

# Reset Docker network
docker network prune
docker compose down
docker compose up -d
```

## Best Practices

1. **Environment Management**
   - Keep .env file secure and never commit it
   - Use different .env files for different environments
   - Regularly rotate API keys

2. **Workspace Organization**
   - Keep projects in /workspace subdirectories
   - Use descriptive folder names
   - Regular backups of important work

3. **Resource Management**
   - Monitor container resource usage
   - Clean up unused Docker resources
   - Set appropriate resource limits

4. **Security**
   - Use strong API keys
   - Keep container updated
   - Don't expose sensitive ports to public networks

5. **Development Workflow**
   - Use version control for your projects
   - Test changes in development environment
   - Document your workflows and configurations

## Getting Help

- Check the [README](../README.md) for detailed setup instructions
- Review [troubleshooting guide](../docs/TROUBLESHOOTING.md)
- Open an issue on GitHub for bug reports
- Join the community discussions