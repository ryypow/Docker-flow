Below is a minimal, production-quality setup you can drop into your repo.
________________________________________
1) Dockerfile
# DockerFlow: Claude-Flow toolbox image
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NODE_VERSION=20 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Etc/UTC

# Base deps (git, curl, Python3, compilers, shell utils)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git bash sudo tzdata \
    python3 python3-pip python3-venv build-essential \
    jq ripgrep fd-find unzip openssh-client \
 && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
 && rm -rf /var/lib/apt/lists/*

# Node.js LTS (NodeSource)
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
 && apt-get update && apt-get install -y --no-install-recommends nodejs \
 && npm i -g npm@latest pnpm yarn

# Non-root user
ARG USER=appuser
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} ${USER} \
 && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USER} \
 && echo "${USER} ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/${USER}

# Workspace & cache dirs
WORKDIR /workspace
RUN chown -R ${USER}:${USER} /workspace
USER ${USER}

# Optional: pre-create a Python venv to keep things tidy
RUN python3 -m venv ~/.venv && echo 'source ~/.venv/bin/activate' >> ~/.bashrc

# Default envs (filled by compose)
ENV ANTHROPIC_API_KEY= \
    OPENAI_API_KEY= \
    HF_TOKEN=

# Helpful shell quality-of-life
RUN echo 'alias ll="ls -alF"' >> ~/.bashrc \
 && echo 'alias cls="clear"'  >> ~/.bashrc

# Default command: keep container alive for interactive use
CMD ["bash", "-lc", "echo 'Claude-Flow toolbox ready. Mount your repo at /workspace and run npx claude-flow ...'; tail -f /dev/null"]
Why this image?
•	Installs Node 20 LTS, Python 3, pip, build-essential, jq, ripgrep, fd — the usual tools Claude-Flow hooks expect.
•	Creates a non-root user so volumes are writable on Linux/WSL/ Codespaces.
•	Leaves you in /workspace ready to run npx claude-flow ....
________________________________________
2) docker-compose.yml
version: "3.9"

name: dockerflow

services:
  claude-flow:
    build: .
    image: dockerflow/claude-flow:dev
    container_name: dockerflow
    working_dir: /workspace
    # Mount your project into the toolbox
    volumes:
      - ./workspace:/workspace:rw
      # cache node/pip between rebuilds (optional)
      - node-cache:/home/appuser/.npm
      - pip-cache:/home/appuser/.cache/pip
    environment:
      # Fill these in a .env file next to this compose file
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      HF_TOKEN: ${HF_TOKEN}
      # If Claude-Flow reads additional vars, add them here.
      NODE_ENV: development
    # Uncomment to enable GPU if host supports nvidia-container-toolkit
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - capabilities: [gpu]
    #           driver: nvidia
    #           count: 1
    tty: true
    stdin_open: true
    # Healthcheck just verifies the shell is usable
    healthcheck:
      test: ["CMD-SHELL", "bash -lc 'node -v && python3 --version && jq --version && rg --version && fd --version'"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  node-cache:
  pip-cache:
This runs as a toolbox container. You open a shell into it and run Claude-Flow commands against the mounted repo.
________________________________________
3) .env (next to compose file)
ANTHROPIC_API_KEY=sk-your-anthropic-key
OPENAI_API_KEY=
HF_TOKEN=
(Don’t commit real secrets.)
________________________________________
4) Project structure
DockerFlow/
  Dockerfile
  docker-compose.yml
  .env                 # your API keys (local only)
  .dockerignore
  workspace/           # put/clone your target repo here (e.g., claude-flow)
.dockerignore
node_modules
.env
.git
workspace/**/node_modules
workspace/**/.venv
________________________________________
5) Usage
# 1) Build the toolbox image
docker compose build

# 2) Put your target repo into ./workspace (clone or copy)
git clone https://github.com/ruvnet/claude-flow ./workspace/claude-flow

# 3) Start container
docker compose up -d

# 4) Exec into the toolbox
docker exec -it dockerflow bash

# 5) Inside the container, work on the repo:
cd claude-flow

# Optional: install project deps if the repo needs them
npm install  # or pnpm/yarn as appropriate

# 6) Run Claude-Flow commands
npx claude-flow scan
npx claude-flow repair --dry-run
# or any specialized flows that repo documents, e.g.:
# npx claude-flow sparc run "audit" --validate-safety true --prepare-resources true
If the repo includes scripts (build/test/typecheck), run them inside the container after repairs:
npm run build
npm test
npm run typecheck
________________________________________
Notes & options
•	Dependencies: The image includes the common utilities Claude-Flow hooks call (jq, ripgrep, fd) and compilers for native Node modules.
•	GPU: Uncomment the GPU section and run with the NVIDIA toolkit if you later integrate GPU-aware tasks.
•	Codespaces: This same setup works in Codespaces by adding a .devcontainer/devcontainer.json that runs docker compose up -d and attaches to the container.
•	Security: Keep real keys in .env locally; use GitHub Actions/Secrets for CI if you automate.
•	Non-root: Files written into ./workspace will be owned by your user (UID 1000), avoiding permissions pain on Linux/WSL.
Awesome—here’s a minimal “all-in-one” setup that builds a Claude-Flow toolbox container and exposes:
•	UI at http://localhost:5000
•	WebSocket at ws://localhost:5001
•	API status (and REST) at http://localhost:5002
It lets users trigger claude-flow / claude commands from the UI and stream logs over websockets.
________________________________________
1) docker-compose.yml
version: "3.9"

name: dockerflow

services:
  dockerflow:
    build: .
    container_name: dockerflow
    working_dir: /workspace
    ports:
      - "5000:5000"  # UI
      - "5001:5001"  # WebSocket
      - "5002:5002"  # REST /status
    env_file: .env
    environment:
      NODE_ENV: production
    volumes:
      - ./workspace:/workspace:rw
      - node-cache:/home/appuser/.npm
      - pip-cache:/home/appuser/.cache/pip
    tty: true
    stdin_open: true
    healthcheck:
      test: ["CMD-SHELL", "bash -lc 'node -v && python3 --version && jq --version && rg --version && fd --version'"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  node-cache:
  pip-cache:
________________________________________
2) Dockerfile
# Claude-Flow toolbox + tiny API/WS + static UI
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NODE_VERSION=20 \
    LANG=C.UTF-8 LC_ALL=C.UTF-8 TZ=Etc/UTC

# OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git bash sudo tzdata \
    python3 python3-pip python3-venv build-essential \
    jq ripgrep fd-find unzip openssh-client \
 && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
 && rm -rf /var/lib/apt/lists/*

# Node LTS
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
 && apt-get update && apt-get install -y --no-install-recommends nodejs \
 && npm i -g npm@latest pnpm yarn

# Non-root user
ARG USER=appuser
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} ${USER} \
 && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USER} \
 && echo "${USER} ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/${USER}

WORKDIR /app
COPY server/requirements.txt /app/server/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /app/server/requirements.txt

# Build UI (static) → served by FastAPI StaticFiles
COPY ui /app/ui

WORKDIR /workspace
RUN chown -R ${USER}:${USER} /app /workspace
USER ${USER}

# Simple shell QoL
RUN echo 'alias ll="ls -alF"' >> ~/.bashrc

# API/WS server code
COPY --chown=${USER}:${USER} server /app/server

# Default command: run FastAPI (REST on :5002, WS on :5001, static UI on :5000)
CMD ["bash","-lc","python3 -m uvicorn server.main:app --host 0.0.0.0 --port 5002 & python3 /app/server/ws.py & python3 /app/server/ui.py"]
________________________________________
3) server/requirements.txt
fastapi==0.111.0
uvicorn==0.30.0
pydantic==2.7.0
starlette==0.37.2
________________________________________
4) server/main.py (REST on :5002)
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import subprocess, shlex, os

app = FastAPI(title="DockerFlow API", version="1.0")

@app.get("/status")
def status():
    return {"ok": True, "node": _run("node -v"), "python": _run("python3 --version"), "cwd": os.getcwd()}

@app.post("/run")
def run(body: dict):
    """
    body: { "cmd": "npx claude-flow scan" }
    Executes from /workspace (mounted repo). Returns exit code + last 4KB.
    """
    cmd = body.get("cmd")
    if not cmd:
        return JSONResponse({"ok": False, "error": "missing cmd"}, status_code=400)
    out = _run(cmd, cwd="/workspace")
    return {"ok": True, "cmd": cmd, "output": out}

def _run(cmd: str, cwd: str | None = None) -> str:
    try:
        p = subprocess.run(shlex.split(cmd), cwd=cwd, capture_output=True, text=True)
        data = (p.stdout or "") + (p.stderr or "")
        return data[-4096:]  # cap
    except Exception as e:
        return f"error: {e}"
________________________________________
5) server/ws.py (WebSocket on :5001; streams command output live)
import asyncio, shlex, os
from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from starlette.websockets import WebSocketState
import uvicorn
import subprocess

app = FastAPI(title="DockerFlow WS")

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        # first message must be {"cmd": "..."}
        msg = await ws.receive_json()
        cmd = msg.get("cmd")
        if not cmd:
            await ws.send_text("error: missing 'cmd'")
            await ws.close(); return

        process = await asyncio.create_subprocess_exec(
            *shlex.split(cmd),
            cwd="/workspace",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=os.environ.copy()
        )
        await ws.send_text(f"$ {cmd}\n")
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            if ws.application_state != WebSocketState.CONNECTED:
                break
            await ws.send_text(line.decode(errors="ignore"))
        code = await process.wait()
        await ws.send_text(f"\n[exit {code}]")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        if ws.application_state == WebSocketState.CONNECTED:
            await ws.send_text(f"error: {e}")
    finally:
        if ws.application_state == WebSocketState.CONNECTED:
            await ws.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
________________________________________
6) server/ui.py (serves static UI on :5000)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn, os

app = FastAPI(title="DockerFlow UI")
static_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
________________________________________
7) ui/index.html (super-light UI)
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>DockerFlow UI</title>
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      body { font-family: ui-sans-serif, system-ui; max-width: 960px; margin: 20px auto; }
      textarea, input { width: 100%; }
      #log { white-space: pre-wrap; background: #0b1020; color: #d1d5db; padding: 12px; border-radius: 8px; height: 380px; overflow:auto; }
      button { padding: 8px 12px; margin-right: 6px; }
    </style>
  </head>
  <body>
    <h1>DockerFlow – Claude-Flow Control</h1>

    <p>Quick commands:</p>
    <p>
      <button onclick="run('npx claude-flow scan')">Scan</button>
      <button onclick="run('npx claude-flow repair --dry-run')">Repair (dry run)</button>
      <button onclick="run('npx claude --help')">Claude Help</button>
    </p>

    <label>Custom command</label>
    <input id="cmd" placeholder="e.g. npx claude-flow sparc run &quot;audit&quot;" />
    <p>
      <button onclick="runInput()">Run via REST</button>
      <button onclick="streamInput()">Stream via WebSocket</button>
    </p>

    <h3>Status</h3>
    <pre id="status"></pre>

    <h3>Output</h3>
    <div id="log"></div>

    <script>
      const apiBase = 'http://localhost:5002';
      const wsUrl = 'ws://localhost:5001/ws';
      const logEl = document.getElementById('log');

      async function fetchStatus() {
        const r = await fetch(apiBase + '/status');
        document.getElementById('status').textContent = JSON.stringify(await r.json(), null, 2);
      }

      async function run(cmd) {
        logEl.textContent = `> ${cmd}\n`;
        const r = await fetch(apiBase + '/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({cmd})
        });
        const data = await r.json();
        logEl.textContent += (data.output || JSON.stringify(data,null,2));
      }

      function runInput(){ run(document.getElementById('cmd').value || 'echo "no cmd"'); }

      function streamInput(){
        stream(document.getElementById('cmd').value || 'echo "no cmd"');
      }

      function stream(cmd){
        logEl.textContent = `$ ${cmd}\n`;
        const ws = new WebSocket(wsUrl);
        ws.onopen = () => ws.send(JSON.stringify({cmd}));
        ws.onmessage = (ev) => { logEl.textContent += ev.data; logEl.scrollTop = logEl.scrollHeight; };
        ws.onerror = (e) => logEl.textContent += '\n[ws error]';
      }

      fetchStatus();
    </script>
  </body>
</html>
________________________________________
8) .env
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=
HF_TOKEN=
________________________________________
How it works
•	ui.py serves the static UI on :5000.
•	main.py exposes /status + /run on :5002 (runs commands in /workspace).
•	ws.py exposes WebSocket /ws on :5001 and streams live output of a command (e.g., npx claude-flow repair).
•	Your repo (e.g., ruvnet/claude-flow) lives under ./workspace on the host and is mounted into /workspace in the container.
________________________________________
Bring it up
# In your DockerFlow repo
docker compose build
# put/clone your target project into ./workspace
git clone https://github.com/ruvnet/claude-flow ./workspace/claude-flow
docker compose up -d

# open:
# UI:       http://localhost:5000
# WebSocket ws://localhost:5001/ws
# API:      http://localhost:5002/status
From the UI, click quick actions or enter any claude-flow / claude command.
From the terminal, you can also docker exec -it dockerflow bash and run commands directly in /workspace.
________________________________________
Notes / Next steps
•	If claude-flow requires project-specific npm install, do it once inside /workspace/claude-flow.
•	Harden the /run and /ws endpoints if you’ll expose this beyond localhost (auth, command allow-list).
•	Add GPU support later (uncomment compose deploy.reservations.devices and install NVIDIA toolkit on host).
