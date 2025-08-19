"""
DockerFlow UI Server
Serves the static web interface
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DockerFlow UI Server",
    version="2.0.0",
    description="Static file server and UI for DockerFlow"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# UI server metrics
ui_metrics = {
    "requests_total": 0,
    "static_files_served": 0,
    "errors_total": 0,
    "uptime_start": datetime.now()
}

# Get the UI directory path
ui_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui")

# Ensure UI directory exists
os.makedirs(ui_dir, exist_ok=True)

# Mount static files with error handling
if os.path.exists(ui_dir):
    try:
        app.mount("/static", StaticFiles(directory=ui_dir), name="static")
        logger.info(f"Static files mounted from {ui_dir}")
    except Exception as e:
        logger.error(f"Failed to mount static files: {e}")
else:
    logger.warning(f"UI directory not found: {ui_dir}")

@app.get("/")
async def root():
    """Serve the main UI"""
    ui_metrics["requests_total"] += 1
    
    try:
        index_file = os.path.join(ui_dir, "index.html")
        if os.path.exists(index_file):
            logger.debug(f"Serving index.html from {index_file}")
            return FileResponse(index_file)
        else:
            logger.info("index.html not found, serving default UI")
            return HTMLResponse(content=DEFAULT_UI)
    except Exception as e:
        ui_metrics["errors_total"] += 1
        logger.error(f"Error serving root page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/terminal")
async def terminal():
    """Serve the terminal UI"""
    ui_metrics["requests_total"] += 1
    
    try:
        terminal_file = os.path.join(ui_dir, "terminal.html")
        if os.path.exists(terminal_file):
            logger.debug(f"Serving terminal.html from {terminal_file}")
            ui_metrics["static_files_served"] += 1
            return FileResponse(terminal_file)
        else:
            logger.info("terminal.html not found, serving default terminal")
            return HTMLResponse(content=DEFAULT_TERMINAL)
    except Exception as e:
        ui_metrics["errors_total"] += 1
        logger.error(f"Error serving terminal page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Default UI HTML if file doesn't exist
DEFAULT_UI = """
<!DOCTYPE html>
<html>
<head>
    <title>DockerFlow UI</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 800px;
            width: 90%;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .status {
            background: #f0f0f0;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-family: 'Courier New', monospace;
        }
        .buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-bottom: 30px;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .terminal-link {
            display: inline-block;
            margin-top: 20px;
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }
        #output {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            min-height: 200px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        input {
            flex: 1;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 DockerFlow Control Center</h1>
        <p class="subtitle">Claude-Flow & Claude-Code Environment</p>
        
        <div class="status" id="status">Loading status...</div>
        
        <div class="buttons">
            <button onclick="runCommand('npx claude-flow --version')">Check Version</button>
            <button onclick="runCommand('npx claude-flow scan')">Scan Project</button>
            <button onclick="runCommand('npx claude-flow sparc modes')">SPARC Modes</button>
            <button onclick="runCommand('npx claude-flow --help')">Help</button>
        </div>
        
        <div id="output">Ready for commands...</div>
        
        <div class="input-group">
            <input type="text" id="command" placeholder="Enter command (e.g., npx claude-flow sparc run architect 'task')" onkeypress="if(event.key==='Enter') runCustom()">
            <button onclick="runCustom()">Run Command</button>
        </div>
        
        <a href="http://localhost:7681" target="_blank" class="terminal-link">
            📟 Open Full Terminal →
        </a>
    </div>
    
    <script>
        const output = document.getElementById('output');
        const statusEl = document.getElementById('status');
        let ws = null;
        
        // Check API status
        async function checkStatus() {
            try {
                const res = await fetch('http://localhost:5002/status');
                const data = await res.json();
                statusEl.textContent = `✅ System Ready | Node: ${data.system.node} | Claude-Flow: ${data.system.claude_flow}`;
            } catch (e) {
                statusEl.textContent = '⚠️ Waiting for services...';
                setTimeout(checkStatus, 2000);
            }
        }
        
        // Connect WebSocket
        function connectWS() {
            ws = new WebSocket('ws://localhost:5001/ws');
            
            ws.onopen = () => {
                output.textContent = '✅ Connected to WebSocket\\n';
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'output') {
                    output.textContent += data.data;
                } else if (data.type === 'command') {
                    output.textContent += `\\n$ ${data.cmd}\\n`;
                } else if (data.type === 'complete') {
                    output.textContent += `\\n[Process exited with code ${data.exit_code}]\\n`;
                }
                output.scrollTop = output.scrollHeight;
            };
            
            ws.onerror = () => {
                output.textContent += '\\n❌ WebSocket error\\n';
            };
            
            ws.onclose = () => {
                output.textContent += '\\n⚠️ WebSocket disconnected, reconnecting...\\n';
                setTimeout(connectWS, 2000);
            };
        }
        
        function runCommand(cmd) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ cmd, cwd: '/workspace' }));
            } else {
                output.textContent = '⚠️ Not connected. Trying REST API...\\n';
                runViaREST(cmd);
            }
        }
        
        function runCustom() {
            const cmd = document.getElementById('command').value;
            if (cmd) {
                runCommand(cmd);
                document.getElementById('command').value = '';
            }
        }
        
        async function runViaREST(cmd) {
            try {
                const res = await fetch('http://localhost:5002/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cmd })
                });
                const data = await res.json();
                output.textContent += `\\n$ ${cmd}\\n${data.output}\\n`;
            } catch (e) {
                output.textContent += `\\nError: ${e.message}\\n`;
            }
        }
        
        // Initialize
        checkStatus();
        connectWS();
    </script>
</body>
</html>
"""

DEFAULT_TERMINAL = """
<!DOCTYPE html>
<html>
<head>
    <title>DockerFlow Terminal</title>
    <meta charset="utf-8">
    <style>
        body { margin: 0; padding: 0; background: #1e1e1e; }
        iframe {
            width: 100vw;
            height: 100vh;
            border: none;
        }
        .fallback {
            color: white;
            text-align: center;
            padding: 50px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <iframe src="http://localhost:7681" id="terminal-frame"></iframe>
    <div class="fallback" id="fallback" style="display:none;">
        <h1>Terminal Loading...</h1>
        <p>If terminal doesn't load, access it directly at: <a href="http://localhost:7681" style="color: #667eea;">http://localhost:7681</a></p>
    </div>
    <script>
        setTimeout(() => {
            const frame = document.getElementById('terminal-frame');
            frame.onerror = () => {
                document.getElementById('fallback').style.display = 'block';
                frame.style.display = 'none';
            };
        }, 3000);
    </script>
</body>
</html>
"""

@app.get("/health")
async def health():
    """UI server health check"""
    uptime = datetime.now() - ui_metrics["uptime_start"]
    
    try:
        # Check if UI directory is accessible
        ui_accessible = os.path.exists(ui_dir) and os.path.isdir(ui_dir)
        
        # Check key files
        index_exists = os.path.exists(os.path.join(ui_dir, "index.html"))
        terminal_exists = os.path.exists(os.path.join(ui_dir, "terminal.html"))
        
        status = "healthy"
        if not ui_accessible:
            status = "unhealthy"
        elif ui_metrics["errors_total"] > 50:
            status = "degraded"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "uptime": str(uptime),
            "ui_directory": {
                "path": ui_dir,
                "accessible": ui_accessible,
                "index_exists": index_exists,
                "terminal_exists": terminal_exists
            },
            "metrics": ui_metrics.copy()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/api/status")
async def api_status():
    """Get status of all DockerFlow services"""
    import httpx
    
    services = {
        "api": "http://localhost:5002/health",
        "websocket": "http://localhost:5001/health",
        "terminal": "http://localhost:5003/health"
    }
    
    status_data = {
        "ui": {
            "status": "healthy",
            "uptime": str(datetime.now() - ui_metrics["uptime_start"]),
            "requests_total": ui_metrics["requests_total"]
        }
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service, url in services.items():
            try:
                response = await client.get(url)
                status_data[service] = response.json()
            except Exception as e:
                status_data[service] = {
                    "status": "unavailable",
                    "error": str(e)
                }
    
    return status_data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)