"""
DockerFlow REST API Server
Provides endpoints for command execution and system management
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import shlex
import os
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import traceback
import psutil
import platform

app = FastAPI(
    title="DockerFlow API",
    version="2.0.0",
    description="REST API for claude-flow and claude-code execution"
)

# Enable CORS for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class CommandRequest(BaseModel):
    cmd: str
    cwd: Optional[str] = "/workspace"
    timeout: Optional[int] = 300
    env: Optional[Dict[str, str]] = None

class CommandResponse(BaseModel):
    ok: bool
    cmd: str
    output: str
    exit_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: str

# Global state for tracking running commands
running_commands = {}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Health metrics
health_metrics = {
    "requests_total": 0,
    "requests_failed": 0,
    "commands_executed": 0,
    "commands_failed": 0,
    "uptime_start": datetime.now()
}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "DockerFlow API",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "run": "/run",
            "info": "/info",
            "commands": "/commands"
        }
    }

@app.get("/health")
async def health():
    """Enhanced health check endpoint"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Calculate uptime
        uptime = datetime.now() - health_metrics["uptime_start"]
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": str(uptime),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024 * 1024 * 1024),
                "platform": platform.platform(),
                "python_version": platform.python_version()
            },
            "metrics": health_metrics.copy(),
            "running_commands": len(running_commands)
        }
        
        # Determine overall health
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 95:
            health_data["status"] = "degraded"
            logger.warning(f"System resources high: CPU {cpu_percent}%, Memory {memory.percent}%, Disk {disk.percent}%")
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/status")
async def status():
    """System status endpoint"""
    def run_cmd(cmd: str) -> str:
        try:
            result = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception as e:
            return f"Error: {str(e)}"
    
    return {
        "ok": True,
        "system": {
            "node": run_cmd("node -v"),
            "npm": run_cmd("npm -v"),
            "python": run_cmd("python3 --version"),
            "claude_flow": run_cmd("npx claude-flow --version"),
            "cwd": os.getcwd(),
            "user": os.environ.get("USER", "unknown"),
            "home": os.environ.get("HOME", "/home/dockerflow")
        },
        "environment": {
            "ANTHROPIC_API_KEY": "***" if os.environ.get("ANTHROPIC_API_KEY") else None,
            "OPENAI_API_KEY": "***" if os.environ.get("OPENAI_API_KEY") else None,
            "NODE_ENV": os.environ.get("NODE_ENV", "production")
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/info")
async def info():
    """Get claude-flow information"""
    commands = {
        "scan": "npx claude-flow scan",
        "repair": "npx claude-flow repair --dry-run",
        "sparc_modes": "npx claude-flow sparc modes",
        "help": "npx claude-flow --help"
    }
    
    return {
        "claude_flow": {
            "version": "alpha",
            "commands": commands
        },
        "sparc_modes": [
            "spec-pseudocode",
            "architect",
            "code",
            "tdd",
            "debug",
            "security-review",
            "docs-writer",
            "integration"
        ]
    }

@app.post("/run")
async def run_command(request: CommandRequest):
    """Execute a command and return output"""
    health_metrics["requests_total"] += 1
    
    try:
        cmd = request.cmd
        cwd = request.cwd
        timeout = request.timeout
        
        if not cmd:
            raise HTTPException(status_code=400, detail="Command is required")
        
        # Security: Basic command validation
        dangerous_cmds = ["rm -rf", "dd if=", "mkfs", "format"]
        if any(danger in cmd.lower() for danger in dangerous_cmds):
            raise HTTPException(status_code=403, detail="Command not allowed for security reasons")
        
        # Prepare environment
        env = os.environ.copy()
        if request.env:
            env.update(request.env)
        
        # Execute command
        process = subprocess.run(
            shlex.split(cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        
        # Prepare response
        output = process.stdout + process.stderr
        
        # Truncate output if too large (max 100KB)
        if len(output) > 100000:
            output = output[:100000] + "\n... [Output truncated]"
        
        health_metrics["commands_executed"] += 1
        logger.info(f"Command executed successfully: {cmd[:50]}...")
        
        return CommandResponse(
            ok=process.returncode == 0,
            cmd=cmd,
            output=output,
            exit_code=process.returncode,
            timestamp=datetime.now().isoformat()
        )
        
    except subprocess.TimeoutExpired as e:
        health_metrics["commands_failed"] += 1
        logger.warning(f"Command timeout: {cmd[:50]}... after {timeout}s")
        
        return CommandResponse(
            ok=False,
            cmd=cmd,
            output="",
            error=f"Command timed out after {timeout} seconds",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        health_metrics["requests_failed"] += 1
        health_metrics["commands_failed"] += 1
        logger.error(f"Command execution failed: {cmd[:50]}... - {str(e)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        return CommandResponse(
            ok=False,
            cmd=cmd,
            output="",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )
    
    finally:
        # Always log request completion
        logger.debug(f"Request completed for command: {request.cmd[:30]}...")

@app.get("/commands")
async def list_commands():
    """List available claude-flow commands"""
    commands = [
        {
            "category": "Core",
            "commands": [
                {"cmd": "npx claude-flow scan", "desc": "Scan project for issues"},
                {"cmd": "npx claude-flow repair", "desc": "Repair project issues"},
                {"cmd": "npx claude-flow --help", "desc": "Show help"}
            ]
        },
        {
            "category": "SPARC",
            "commands": [
                {"cmd": "npx claude-flow sparc modes", "desc": "List SPARC modes"},
                {"cmd": "npx claude-flow sparc run spec-pseudocode 'task'", "desc": "Run specification"},
                {"cmd": "npx claude-flow sparc run architect 'task'", "desc": "Run architecture"},
                {"cmd": "npx claude-flow sparc tdd 'feature'", "desc": "Run TDD workflow"}
            ]
        },
        {
            "category": "Swarm",
            "commands": [
                {"cmd": "npx claude-flow swarm init mesh", "desc": "Initialize swarm"},
                {"cmd": "npx claude-flow agent spawn coder", "desc": "Spawn agent"},
                {"cmd": "npx claude-flow swarm status", "desc": "Check swarm status"}
            ]
        }
    ]
    
    return {"commands": commands}

@app.post("/execute-async")
async def execute_async(request: CommandRequest, background_tasks: BackgroundTasks):
    """Execute command asynchronously"""
    import uuid
    
    task_id = str(uuid.uuid4())
    
    async def run_background(task_id: str, cmd: str, cwd: str):
        # Store in running_commands
        running_commands[task_id] = {
            "status": "running",
            "cmd": cmd,
            "started": datetime.utcnow().isoformat()
        }
        
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await process.communicate()
            
            running_commands[task_id] = {
                "status": "completed",
                "cmd": cmd,
                "output": stdout.decode() + stderr.decode(),
                "exit_code": process.returncode,
                "completed": datetime.utcnow().isoformat()
            }
        except Exception as e:
            running_commands[task_id] = {
                "status": "error",
                "cmd": cmd,
                "error": str(e),
                "completed": datetime.utcnow().isoformat()
            }
    
    background_tasks.add_task(run_background, task_id, request.cmd, request.cwd)
    
    return {
        "task_id": task_id,
        "status": "started",
        "cmd": request.cmd
    }

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get status of async task"""
    if task_id not in running_commands:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return running_commands[task_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)