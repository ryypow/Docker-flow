"""
DockerFlow WebSocket Server
Provides real-time command streaming and terminal sessions
"""

import asyncio
import shlex
import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from starlette.websockets import WebSocketState
import uvicorn
import subprocess
from typing import Dict, Set
from datetime import datetime
import logging
import traceback
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="DockerFlow WebSocket Server")

# Track active connections and metrics
active_connections: Set[WebSocket] = set()
sessions: Dict[str, dict] = {}
ws_metrics = {
    "connections_total": 0,
    "connections_current": 0,
    "messages_sent": 0,
    "messages_received": 0,
    "commands_executed": 0,
    "errors_total": 0,
    "uptime_start": datetime.now()
}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for command streaming"""
    client_info = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    logger.info(f"WebSocket connection attempt from {client_info}")
    
    try:
        await websocket.accept()
        active_connections.add(websocket)
        ws_metrics["connections_total"] += 1
        ws_metrics["connections_current"] += 1
        
        session_id = f"session_{len(active_connections)}_{datetime.now().timestamp()}"
        logger.info(f"WebSocket connection established: {session_id}")
        
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket connected. Send {\"cmd\": \"your command\"} to execute."
        })
        ws_metrics["messages_sent"] += 1
        
        while True:
            # Receive command
            try:
                data = await websocket.receive_json()
                ws_metrics["messages_received"] += 1
                cmd = data.get("cmd")
                cwd = data.get("cwd", "/workspace")
                
                logger.debug(f"Received command: {cmd[:50] if cmd else 'None'}...")
            except Exception as e:
                logger.error(f"Error receiving WebSocket message: {e}")
                ws_metrics["errors_total"] += 1
                await websocket.send_json({
                    "type": "error",
                    "message": f"Invalid message format: {str(e)}"
                })
                continue
            
            if not cmd:
                await websocket.send_json({
                    "type": "error",
                    "message": "Missing 'cmd' field"
                })
                continue
            
            # Log command
            await websocket.send_json({
                "type": "command",
                "cmd": cmd,
                "timestamp": datetime.now().isoformat()
            })
            ws_metrics["messages_sent"] += 1
            ws_metrics["commands_executed"] += 1
            
            # Execute command and stream output
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=cwd,
                    env=os.environ.copy()
                )
                
                # Stream output line by line
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    
                    # Check if websocket is still connected
                    if websocket.application_state != WebSocketState.CONNECTED:
                        process.terminate()
                        break
                    
                    # Send output line
                    await websocket.send_json({
                        "type": "output",
                        "data": line.decode("utf-8", errors="ignore")
                    })
                    ws_metrics["messages_sent"] += 1
                
                # Wait for process to complete
                exit_code = await process.wait()
                
                # Send completion status
                await websocket.send_json({
                    "type": "complete",
                    "exit_code": exit_code,
                    "timestamp": datetime.now().isoformat()
                })
                ws_metrics["messages_sent"] += 1
                
                logger.info(f"Command completed: {cmd[:50]}... (exit code: {exit_code})")
                
            except Exception as e:
                logger.error(f"Error executing command '{cmd}': {e}")
                ws_metrics["errors_total"] += 1
                
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    ws_metrics["messages_sent"] += 1
                except:
                    logger.error("Failed to send error message to client")
    
    except WebSocketDisconnect:
        logger.info(f"Client {session_id} disconnected normally")
    except Exception as e:
        logger.error(f"Error in websocket connection {session_id}: {e}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        ws_metrics["errors_total"] += 1
    finally:
        # Cleanup
        if websocket in active_connections:
            active_connections.discard(websocket)
            ws_metrics["connections_current"] -= 1
            
        if websocket.application_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing websocket: {e}")
                
        logger.info(f"WebSocket connection cleanup completed for {session_id}")

@app.websocket("/terminal")
async def terminal_websocket(websocket: WebSocket):
    """Terminal WebSocket endpoint for interactive shell"""
    await websocket.accept()
    
    try:
        # Start interactive bash shell
        process = await asyncio.create_subprocess_exec(
            "/bin/bash",
            "-l",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd="/workspace",
            env={**os.environ, "TERM": "xterm-256color"}
        )
        
        # Send welcome message
        await websocket.send_text(
            "\033[1;36m🚀 DockerFlow Terminal\033[0m\n"
            "Type 'help' for claude-flow commands\n\n"
        )
        
        # Create tasks for reading and writing
        async def read_from_process():
            while True:
                try:
                    data = await process.stdout.read(1024)
                    if not data:
                        break
                    if websocket.application_state == WebSocketState.CONNECTED:
                        await websocket.send_text(data.decode("utf-8", errors="ignore"))
                except Exception:
                    break
        
        async def write_to_process():
            while True:
                try:
                    data = await websocket.receive_text()
                    if process.stdin:
                        process.stdin.write(data.encode())
                        await process.stdin.drain()
                except WebSocketDisconnect:
                    break
                except Exception:
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(
            read_from_process(),
            write_to_process()
        )
        
    except Exception as e:
        print(f"Terminal error: {e}")
    finally:
        if process:
            process.terminate()
            await process.wait()
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()

@app.websocket("/stream")
async def stream_websocket(websocket: WebSocket):
    """Streaming endpoint for real-time updates"""
    await websocket.accept()
    
    try:
        # Subscribe to events
        await websocket.send_json({
            "type": "subscribed",
            "channels": ["commands", "logs", "metrics"]
        })
        
        # Keep connection alive and send periodic updates
        while True:
            # Send heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
                "connections": len(active_connections)
            })
            
            # Wait for 30 seconds or until message received
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                
                # Handle different message types
                msg_type = message.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "subscribe":
                    channels = message.get("channels", [])
                    await websocket.send_json({
                        "type": "subscribed",
                        "channels": channels
                    })
                    
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()

@app.get("/")
async def root():
    """WebSocket server information"""
    uptime = datetime.now() - ws_metrics["uptime_start"]
    
    return {
        "name": "DockerFlow WebSocket Server",
        "version": "2.0.0",
        "status": "running",
        "uptime": str(uptime),
        "endpoints": {
            "/ws": "Command execution with streaming output",
            "/terminal": "Interactive terminal session",
            "/stream": "Real-time event streaming",
            "/health": "Health check endpoint",
            "/metrics": "Performance metrics"
        },
        "active_connections": len(active_connections),
        "sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """WebSocket server health check"""
    uptime = datetime.now() - ws_metrics["uptime_start"]
    
    # Determine health status
    status = "healthy"
    if ws_metrics["errors_total"] > 100:  # High error count
        status = "degraded"
    if len(active_connections) > 100:  # Too many connections
        status = "degraded"
    
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "uptime": str(uptime),
        "active_connections": len(active_connections),
        "total_sessions": len(sessions),
        "metrics": ws_metrics.copy()
    }

@app.get("/metrics")
async def metrics():
    """WebSocket server metrics"""
    uptime = datetime.now() - ws_metrics["uptime_start"]
    uptime_seconds = uptime.total_seconds()
    
    return {
        "uptime_seconds": uptime_seconds,
        "connections": {
            "current": len(active_connections),
            "total": ws_metrics["connections_total"],
            "rate_per_hour": ws_metrics["connections_total"] / (uptime_seconds / 3600) if uptime_seconds > 0 else 0
        },
        "messages": {
            "sent": ws_metrics["messages_sent"],
            "received": ws_metrics["messages_received"],
            "send_rate": ws_metrics["messages_sent"] / uptime_seconds if uptime_seconds > 0 else 0,
            "receive_rate": ws_metrics["messages_received"] / uptime_seconds if uptime_seconds > 0 else 0
        },
        "commands": {
            "executed": ws_metrics["commands_executed"],
            "rate_per_hour": ws_metrics["commands_executed"] / (uptime_seconds / 3600) if uptime_seconds > 0 else 0
        },
        "errors": {
            "total": ws_metrics["errors_total"],
            "rate_per_hour": ws_metrics["errors_total"] / (uptime_seconds / 3600) if uptime_seconds > 0 else 0,
            "error_rate_percent": (ws_metrics["errors_total"] / max(ws_metrics["messages_received"], 1)) * 100
        },
        "sessions": {
            "total": len(sessions)
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)