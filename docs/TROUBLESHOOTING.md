# DockerFlow Troubleshooting Guide

This guide helps you resolve common issues when running DockerFlow.

## Quick Diagnostics

### Check System Status
```bash
# Check if services are running
docker compose ps

# Check service health
curl http://localhost:5002/health

# View logs
docker compose logs -f
```

## Common Issues

### 1. Container Won't Start

#### Symptoms
- `docker compose up` fails
- Containers exit immediately
- Port binding errors

#### Solutions

**Check port conflicts:**
```bash
# Check if ports are already in use
netstat -tlnp | grep -E ':5000|:5001|:5002|:7681'

# Kill processes using the ports
sudo lsof -t -i:5000 | xargs kill -9
```

**Verify Docker daemon:**
```bash
# Check Docker status
docker info

# Restart Docker (if needed)
sudo systemctl restart docker
```

**Check resource availability:**
```bash
# Check disk space
df -h

# Check memory
free -h

# Clean up Docker resources
docker system prune -a
```

**Rebuild with clean slate:**
```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### 2. API Key Issues

#### Symptoms
- Authentication errors
- "Invalid API key" messages
- Claude-Flow commands fail

#### Solutions

**Verify .env file:**
```bash
# Check if .env exists
ls -la .env

# Verify API key format
grep ANTHROPIC_API_KEY .env
```

**Correct .env format:**
```env
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here
HF_TOKEN=hf_your-huggingface-token
```

**Restart with new environment:**
```bash
docker compose down
docker compose up -d

# Verify environment variables are loaded
docker exec dockerflow env | grep API_KEY
```

### 3. Permission Issues

#### Symptoms
- "Permission denied" errors
- Cannot write to workspace
- File operation failures

#### Solutions

**Fix workspace permissions:**
```bash
# Fix ownership
sudo chown -R $USER:$USER workspace/

# Fix permissions inside container
docker exec dockerflow chown -R dockerflow:dockerflow /workspace
```

**Check Docker permissions:**
```bash
# Add user to docker group (requires logout/login)
sudo usermod -aG docker $USER
```

### 4. Network Connectivity Issues

#### Symptoms
- Cannot access web UI
- API endpoints unreachable
- WebSocket connection fails

#### Solutions

**Check port bindings:**
```bash
# Verify ports are bound
docker compose ps

# Check if ports are accessible
curl http://localhost:5000
curl http://localhost:5002/health
```

**Reset Docker network:**
```bash
docker network prune
docker compose down
docker compose up -d
```

**Check firewall:**
```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 5000
sudo ufw allow 5002

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### 5. Performance Issues

#### Symptoms
- Slow command execution
- High memory usage
- Container becomes unresponsive

#### Solutions

**Increase resource limits:**

Edit `docker-compose.yml`:
```yaml
services:
  dockerflow:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
        reservations:
          memory: 2G
          cpus: '1'
```

**Monitor resource usage:**
```bash
# Monitor container resources
docker stats dockerflow

# Check system resources
htop
free -h
df -h
```

**Optimize Docker:**
```bash
# Clean up unused resources
docker system prune -a

# Remove unused volumes
docker volume prune

# Remove unused images
docker image prune -a
```

### 6. Claude-Flow Command Failures

#### Symptoms
- Commands timeout
- "Command not found" errors
- Unexpected command output

#### Solutions

**Verify Claude-Flow installation:**
```bash
docker exec dockerflow npx claude-flow --version
docker exec dockerflow which node
docker exec dockerflow npm list -g claude-flow
```

**Update Claude-Flow:**
```bash
# Rebuild with latest version
docker compose build --no-cache
```

**Check command syntax:**
```bash
# Test basic commands
docker exec dockerflow npx claude-flow --help
docker exec dockerflow npx claude-flow sparc modes
```

### 7. WebSocket Connection Issues

#### Symptoms
- Real-time updates not working
- WebSocket connection refused
- Terminal not responsive

#### Solutions

**Test WebSocket endpoint:**
```bash
# Check if WebSocket server is running
curl http://localhost:5001

# Test with websocat (if available)
websocat ws://localhost:5001/ws
```

**Browser debugging:**
```javascript
// Open browser console and test
const ws = new WebSocket('ws://localhost:5001/ws');
ws.onopen = () => console.log('Connected');
ws.onerror = (error) => console.error('WebSocket error:', error);
```

### 8. File System Issues

#### Symptoms
- Files not persisting
- Cannot access workspace files
- File corruption

#### Solutions

**Check volume mounts:**
```bash
# Verify volumes are mounted
docker compose config

# Check volume data
docker volume ls
docker volume inspect dockerflow_workspace
```

**Backup and restore:**
```bash
# Backup workspace
tar -czf workspace-backup.tar.gz workspace/

# Restore if needed
tar -xzf workspace-backup.tar.gz
```

### 9. GPU Support Issues

#### Symptoms
- GPU not detected
- CUDA errors
- Performance not improved

#### Solutions

**Verify GPU setup:**
```bash
# Check NVIDIA drivers
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

**Enable GPU in docker-compose.yml:**
```yaml
services:
  dockerflow:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Debugging Tools

### Container Debugging
```bash
# Access container shell
docker exec -it dockerflow bash

# Check running processes
docker exec dockerflow ps aux

# Check container logs
docker logs dockerflow

# Check disk usage in container
docker exec dockerflow df -h
```

### Network Debugging
```bash
# Test internal connectivity
docker exec dockerflow ping host.docker.internal

# Check port binding
docker port dockerflow

# Test DNS resolution
docker exec dockerflow nslookup google.com
```

### Application Debugging
```bash
# Check Python processes
docker exec dockerflow ps aux | grep python

# Check Node.js processes
docker exec dockerflow ps aux | grep node

# Test API endpoints from inside container
docker exec dockerflow curl http://localhost:5002/health
```

## Log Analysis

### Useful log locations:
```bash
# Docker Compose logs
docker compose logs

# Application logs
docker exec dockerflow tail -f /var/log/application.log

# System logs
journalctl -u docker
```

### Common log patterns:
- `Permission denied`: Check file/directory permissions
- `Connection refused`: Check if service is running
- `Port already in use`: Check for port conflicts
- `Out of memory`: Increase container memory limits
- `Timeout`: Increase timeout values or check performance

## Getting Help

If you're still experiencing issues:

1. **Check GitHub Issues**: Search existing issues for similar problems
2. **Create Detailed Issue**: Include logs, system info, and reproduction steps
3. **Community Support**: Join discussions and ask questions
4. **Documentation**: Review the full documentation

### Information to include in bug reports:
- Operating system and version
- Docker and Docker Compose versions
- DockerFlow version
- Complete error messages and logs
- Steps to reproduce the issue
- Expected vs actual behavior

```bash
# Collect system information
echo "OS: $(uname -a)"
echo "Docker: $(docker --version)"
echo "Docker Compose: $(docker compose version)"
echo "DockerFlow logs:"
docker compose logs --tail=50
```