# 🚀 DockerFlow

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Claude-Flow](https://img.shields.io/badge/Claude--Flow-Integrated-purple.svg)](https://github.com/ruvnet/claude-flow)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![Node 20](https://img.shields.io/badge/Node-20-green.svg)](https://nodejs.org/)

> Complete containerized environment for running Claude-Flow and Claude-Code with a beautiful web interface, terminal access, and full API capabilities.

## 🎯 Overview

DockerFlow provides a production-ready, containerized environment for [Claude-Flow](https://github.com/ruvnet/claude-flow) - the advanced AI orchestration framework. It includes a modern web interface, REST API, WebSocket support, and persistent workspace management, all running in a secure Docker container.

### ✨ Key Features

- **🤖 Full Claude-Flow Integration** - All Claude-Flow and Claude-Code commands pre-installed
- **🌐 Beautiful Web UI** - Modern interface on port 5000 with xterm.js terminal
- **⚡ Real-time Updates** - WebSocket streaming for live command output
- **🔌 REST API** - Full programmatic access with OpenAPI documentation
- **💻 Web Terminal** - Browser-based terminal on port 7681 via ttyd
- **💾 Persistent Storage** - Workspace and configuration persistence
- **🔒 Security First** - Non-root user, proper permissions, environment isolation
- **🚀 GPU Support** - Optional NVIDIA GPU acceleration
- **📊 Health Monitoring** - Built-in health checks and status endpoints

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the DockerFlow directory
cd DockerFlow

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

### 2. Build and Run

```bash
# Build the Docker image
docker compose build

# Start the services
docker compose up -d

# Check service status
docker compose ps
```

### 3. Access Services

- **Web UI**: http://localhost:5000
- **Terminal**: http://localhost:7681
- **API Docs**: http://localhost:5002/docs
- **WebSocket**: ws://localhost:5001

## 📁 Project Structure

```
DockerFlow/
├── Dockerfile              # Container definition
├── docker-compose.yml      # Service orchestration
├── docker-entrypoint.sh    # Startup script
├── .env.example           # Environment template
├── .dockerignore          # Build exclusions
├── server/                # Backend services
│   ├── requirements.txt
│   ├── main.py           # REST API
│   ├── ws.py             # WebSocket server
│   └── ui.py             # Static file server
├── ui/                    # Frontend
│   └── index.html        # Main UI
└── workspace/            # Your projects (mounted)
```

## 🔧 Configuration

### Environment Variables

Edit `.env` file:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE

# Optional
OPENAI_API_KEY=
HF_TOKEN=

# Settings
NODE_ENV=production
CLAUDE_CODE_FLAGS=--dangerously-skip-permissions
```

### Docker Compose Options

```yaml
# Enable GPU support (uncomment in docker-compose.yml)
deploy:
  reservations:
    devices:
      - driver: nvidia
        count: 1
        capabilities: [gpu]
```

## 💻 Usage Examples

### Via Web UI

1. Open http://localhost:5000
2. Use quick command buttons or type custom commands
3. View real-time output in the terminal

### Via CLI

```bash
# Access container shell
docker exec -it dockerflow bash

# Run claude-flow commands
npx claude-flow scan
npx claude-flow sparc modes
npx claude-flow sparc run architect "design auth system"

# Run claude-code
claude --help
```

### Via API

```bash
# Check status
curl http://localhost:5002/status | jq

# Run command
curl -X POST http://localhost:5002/run \
  -H "Content-Type: application/json" \
  -d '{"cmd": "npx claude-flow --version"}'

# Stream via WebSocket
websocat ws://localhost:5001/ws
```

## 🛠️ Development

### Adding Your Project

```bash
# Clone your project into workspace
git clone https://github.com/your-repo workspace/your-project

# Access it in the container
docker exec -it dockerflow bash
cd /workspace/your-project
npm install  # if needed
```

### Customizing the UI

Edit `ui/index.html` to customize the interface. Changes are reflected immediately.

### Adding Python Dependencies

Edit `server/requirements.txt` and rebuild:

```bash
docker compose build
docker compose up -d
```

## 🔍 Troubleshooting

### Services not starting?

```bash
# Check logs
docker compose logs -f

# Restart services
docker compose restart

# Full reset
docker compose down
docker compose up -d --build
```

### Permission issues?

```bash
# Fix workspace permissions
docker exec dockerflow chown -R dockerflow:dockerflow /workspace
```

### API key not working?

```bash
# Verify environment variables
docker exec dockerflow env | grep API_KEY

# Restart with new .env
docker compose down
docker compose up -d
```

## 🚦 Health Checks

The system includes automatic health checks:

```bash
# Check all services
curl http://localhost:5002/health

# View in UI
http://localhost:5000  # Status indicators in header
```

## 🔒 Security Notes

- Never commit `.env` file with real API keys
- Use secrets management in production
- Container runs as non-root user (dockerflow:1000)
- Network isolation via Docker bridge
- Resource limits prevent abuse

## 📊 Performance

- CPU: 2-4 cores recommended
- Memory: 4-8GB recommended
- Disk: 10GB+ for workspace
- Network: Stable connection for API calls

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Test in Docker environment
4. Submit pull request

## 📝 License

MIT License - See LICENSE file for details

## 🆘 Support

- **Documentation**: This README
- **API Reference**: http://localhost:5002/docs
- **Issues**: GitHub Issues

---

## 🎉 Ready to Use!

Your DockerFlow environment is now ready. Open http://localhost:5000 to start using claude-flow and claude-code in a beautiful, containerized environment!

### Quick Commands to Try:

```bash
# In the UI or terminal:
npx claude-flow --version
npx claude-flow scan
npx claude-flow sparc modes
npx claude-flow sparc run architect "design a REST API"
npx claude-flow swarm init mesh
```

Enjoy your enhanced claude-flow experience! 🚀
