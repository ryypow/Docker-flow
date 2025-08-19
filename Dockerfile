# Enhanced DockerFlow: Complete claude-flow/claude-code environment
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NODE_VERSION=20 \
    PYTHON_VERSION=3.11 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Etc/UTC \
    TERM=xterm-256color

# Complete system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Base tools
    ca-certificates curl wget git bash sudo tzdata \
    # Development tools
    build-essential cmake pkg-config \
    # Python and pip
    python3 python3-dev python3-pip python3-venv \
    # Terminal tools
    tmux screen htop vim nano less \
    zsh fish bash-completion \
    ncurses-term xterm \
    # Search and processing
    jq ripgrep fd-find fzf bat exa \
    unzip openssh-client gnupg2 \
    # System libraries
    libssl-dev libffi-dev \
 && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
 && ln -sf /usr/bin/batcat /usr/local/bin/bat \
 && rm -rf /var/lib/apt/lists/*

# Install Node.js LTS
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
 && apt-get update && apt-get install -y nodejs \
 && npm install -g npm@latest pnpm@latest yarn@latest

# Install ttyd for web terminal
RUN wget https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 -O /usr/local/bin/ttyd \
 && chmod +x /usr/local/bin/ttyd

# Create non-root user
ARG USER=dockerflow
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} ${USER} \
 && useradd -m -u ${UID} -g ${GID} -s /bin/bash ${USER} \
 && echo "${USER} ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/${USER} \
 && chmod 0440 /etc/sudoers.d/${USER}

# Install Python packages
COPY server/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --upgrade pip \
 && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

# Install claude-flow and related tools globally
RUN npm install -g claude-flow@alpha \
 && npm cache clean --force

# Setup workspace and app directories
WORKDIR /workspace
RUN mkdir -p /app/server /app/ui /app/config /app/bin \
 && chown -R ${USER}:${USER} /app /workspace

# Copy application files
COPY --chown=${USER}:${USER} server /app/server
COPY --chown=${USER}:${USER} ui /app/ui
COPY --chown=${USER}:${USER} docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER ${USER}

# Configure shell environment
RUN echo 'export PS1="\[\033[1;36m\]dockerflow@\h:\w\$ \[\033[0m\]"' >> ~/.bashrc \
 && echo 'alias ll="ls -alF"' >> ~/.bashrc \
 && echo 'alias cls="clear"' >> ~/.bashrc \
 && echo 'alias cf="npx claude-flow"' >> ~/.bashrc \
 && echo 'alias cfa="npx claude-flow@alpha"' >> ~/.bashrc \
 && echo 'export PATH="$PATH:/app/bin"' >> ~/.bashrc \
 && echo 'cd /workspace' >> ~/.bashrc

# Environment variables (will be overridden by docker-compose)
ENV ANTHROPIC_API_KEY= \
    OPENAI_API_KEY= \
    HF_TOKEN= \
    CLAUDE_CODE_FLAGS="--dangerously-skip-permissions"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -v && python3 --version && npx claude-flow --version

# Entry point
ENTRYPOINT ["/app/docker-entrypoint.sh"]