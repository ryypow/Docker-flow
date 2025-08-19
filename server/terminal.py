"""
DockerFlow Terminal Server
Provides WebSocket PTY management for interactive terminal sessions
"""

import asyncio
import os
import pty
import select
import subprocess
import signal
from typing import Dict, Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DockerFlow Terminal Server", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
active_sessions: Dict[str, dict] = {}
active_connections: Set[WebSocket] = set()

class PTYSession:
    """Manages a PTY session with subprocess communication"""
    
    def __init__(self, session_id: str, shell: str = "/bin/bash", cwd: str = "/workspace"):
        self.session_id = session_id
        self.shell = shell
        self.cwd = cwd
        self.process = None
        self.master_fd = None
        self.websocket = None
        self.running = False
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
    async def start(self):
        """Start the PTY session"""
        try:
            # Create PTY
            self.master_fd, slave_fd = pty.openpty()
            
            # Configure environment
            env = os.environ.copy()
            env.update({
                "TERM": "xterm-256color",
                "PS1": r"\[\033[1;36m\]dockerflow@\h:\w\$ \[\033[0m\]",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8"
            })
            
            # Start shell process
            self.process = subprocess.Popen(
                [self.shell, "-l"],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                preexec_fn=os.setsid,
                cwd=self.cwd,
                env=env
            )
            
            # Close slave fd (parent doesn't need it)
            os.close(slave_fd)
            
            # Set non-blocking mode
            import fcntl
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
            
            self.running = True
            logger.info(f"PTY session {self.session_id} started with PID {self.process.pid}")
            
        except Exception as e:
            logger.error(f"Failed to start PTY session {self.session_id}: {e}")
            raise
    
    def write(self, data: str):
        """Write data to PTY"""
        if self.master_fd and self.running:
            try:
                os.write(self.master_fd, data.encode())
                self.last_activity = datetime.now()
            except OSError as e:
                logger.error(f"Error writing to PTY {self.session_id}: {e}")
                
    def read(self) -> Optional[str]:
        """Read data from PTY"""
        if not self.master_fd or not self.running:
            return None
            
        try:
            # Use select to check if data is available
            ready, _, _ = select.select([self.master_fd], [], [], 0)
            if ready:
                data = os.read(self.master_fd, 1024)
                self.last_activity = datetime.now()
                return data.decode('utf-8', errors='ignore')
        except OSError:
            # PTY closed
            self.running = False
        except Exception as e:
            logger.error(f"Error reading from PTY {self.session_id}: {e}")
        
        return None
    
    def resize(self, cols: int, rows: int):
        """Resize PTY"""
        if self.master_fd and self.running:
            try:
                import struct
                import fcntl
                import termios
                # Set window size
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
                logger.info(f"Resized PTY {self.session_id} to {cols}x{rows}")
            except Exception as e:
                logger.error(f"Error resizing PTY {self.session_id}: {e}")
    
    def close(self):
        """Close PTY session"""
        self.running = False
        
        if self.process:
            try:
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait a bit for graceful shutdown
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait()
                    
            except Exception as e:
                logger.error(f"Error closing process for PTY {self.session_id}: {e}")
        
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except Exception as e:
                logger.error(f"Error closing PTY fd {self.session_id}: {e}")
        
        logger.info(f"PTY session {self.session_id} closed")

@app.websocket("/pty/{session_id}")
async def pty_websocket(websocket: WebSocket, session_id: str = None):
    """WebSocket endpoint for PTY sessions"""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    await websocket.accept()
    active_connections.add(websocket)
    
    # Create PTY session
    pty_session = PTYSession(session_id)
    active_sessions[session_id] = {
        "pty": pty_session,
        "websocket": websocket,
        "created": datetime.now().isoformat()
    }
    
    try:
        # Start PTY
        await pty_session.start()
        pty_session.websocket = websocket
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "PTY session started"
        })
        
        # Create reading task
        async def read_pty():
            """Continuously read from PTY and send to WebSocket"""
            while pty_session.running:
                try:
                    data = pty_session.read()
                    if data:
                        await websocket.send_json({
                            "type": "output",
                            "data": data
                        })
                    else:
                        # Small delay to prevent busy waiting
                        await asyncio.sleep(0.01)
                        
                except Exception as e:
                    logger.error(f"Error in read_pty: {e}")
                    break
        
        # Start reading task
        read_task = asyncio.create_task(read_pty())
        
        # Handle WebSocket messages
        while pty_session.running:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                msg_type = data.get("type")
                
                if msg_type == "input":
                    # Send input to PTY
                    input_data = data.get("data", "")
                    pty_session.write(input_data)
                    
                elif msg_type == "resize":
                    # Resize PTY
                    cols = data.get("cols", 80)
                    rows = data.get("rows", 24)
                    pty_session.resize(cols, rows)
                    
                elif msg_type == "ping":
                    # Respond to ping
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
        
        # Cancel reading task
        read_task.cancel()
        try:
            await read_task
        except asyncio.CancelledError:
            pass
            
    except Exception as e:
        logger.error(f"Error in PTY WebSocket {session_id}: {e}")
        await websocket.send_json({
            "type": "error", 
            "message": str(e)
        })
    finally:
        # Cleanup
        if session_id in active_sessions:
            active_sessions[session_id]["pty"].close()
            del active_sessions[session_id]
        
        active_connections.discard(websocket)
        
        if websocket.client_state.value == 1:  # CONNECTED
            await websocket.close()

@app.websocket("/terminal")
async def terminal_websocket(websocket: WebSocket):
    """Simple terminal WebSocket (compatibility with existing code)"""
    session_id = str(uuid.uuid4())
    await pty_websocket(websocket, session_id)

@app.get("/")
async def root():
    """Terminal server information"""
    return {
        "name": "DockerFlow Terminal Server",
        "version": "1.0.0",
        "active_sessions": len(active_sessions),
        "active_connections": len(active_connections),
        "endpoints": {
            "/pty/{session_id}": "Create/connect to PTY session",
            "/terminal": "Simple terminal connection",
            "/sessions": "List active sessions",
            "/session/{session_id}": "Get session info"
        }
    }

@app.get("/sessions")
async def list_sessions():
    """List all active PTY sessions"""
    sessions = []
    for session_id, session_data in active_sessions.items():
        pty = session_data["pty"]
        sessions.append({
            "session_id": session_id,
            "created": session_data["created"],
            "running": pty.running,
            "last_activity": pty.last_activity.isoformat(),
            "shell": pty.shell,
            "cwd": pty.cwd,
            "pid": pty.process.pid if pty.process else None
        })
    return {"sessions": sessions}

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get information about a specific session"""
    if session_id not in active_sessions:
        return {"error": "Session not found"}, 404
    
    session_data = active_sessions[session_id]
    pty = session_data["pty"]
    
    return {
        "session_id": session_id,
        "created": session_data["created"],
        "running": pty.running,
        "last_activity": pty.last_activity.isoformat(),
        "shell": pty.shell,
        "cwd": pty.cwd,
        "pid": pty.process.pid if pty.process else None,
        "uptime": str(datetime.now() - pty.created_at)
    }

@app.delete("/session/{session_id}")
async def close_session(session_id: str):
    """Close a specific PTY session"""
    if session_id not in active_sessions:
        return {"error": "Session not found"}, 404
    
    session_data = active_sessions[session_id]
    session_data["pty"].close()
    del active_sessions[session_id]
    
    return {"message": f"Session {session_id} closed"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(active_sessions),
        "active_connections": len(active_connections)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5003)