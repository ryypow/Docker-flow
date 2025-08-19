/**
 * DockerFlow Terminal JavaScript
 * Handles xterm.js terminal, WebSocket connections, and UI interactions
 */

class DockerFlowTerminal {
    constructor() {
        this.term = null;
        this.ws = null;
        this.sessionId = null;
        this.fitAddon = null;
        this.webLinksAddon = null;
        this.searchAddon = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.sessionStartTime = null;
        this.uptimeInterval = null;
        this.settings = this.loadSettings();
        
        this.init();
    }
    
    init() {
        this.initTerminal();
        this.setupEventListeners();
        this.connect();
        this.startUptimeCounter();
        this.applySettings();
    }
    
    initTerminal() {
        // Create terminal with settings
        this.term = new Terminal({
            cursorBlink: this.settings.cursorBlink,
            cursorStyle: this.settings.cursorStyle,
            fontSize: this.settings.fontSize,
            fontFamily: this.settings.fontFamily,
            theme: {
                background: '#0d1117',
                foreground: '#c9d1d9',
                cursor: '#58a6ff',
                selection: '#3392ff44',
                black: '#484f58',
                red: '#ff7b72',
                green: '#3fb950',
                yellow: '#d29922',
                blue: '#58a6ff',
                magenta: '#bc8cff',
                cyan: '#39c5cf',
                white: '#b1bac4',
                brightBlack: '#6e7681',
                brightRed: '#ffa198',
                brightGreen: '#56d364',
                brightYellow: '#e3b341',
                brightBlue: '#79c0ff',
                brightMagenta: '#d2a8ff',
                brightCyan: '#56d4dd',
                brightWhite: '#f0f6fc'
            },
            allowTransparency: true,
            convertEol: true,
            scrollback: 10000
        });
        
        // Load addons
        this.fitAddon = new FitAddon.FitAddon();
        this.webLinksAddon = new WebLinksAddon.WebLinksAddon();
        this.searchAddon = new SearchAddon.SearchAddon();
        
        this.term.loadAddon(this.fitAddon);
        this.term.loadAddon(this.webLinksAddon);
        this.term.loadAddon(this.searchAddon);
        
        // Open terminal
        this.term.open(document.getElementById('terminal'));
        this.fitAddon.fit();
        
        // Handle terminal input
        this.term.onData((data) => {
            if (this.isConnected && this.ws) {
                this.ws.send(JSON.stringify({
                    type: 'input',
                    data: data
                }));
            }
        });
        
        // Handle terminal resize
        this.term.onResize(({ cols, rows }) => {
            this.updateTerminalSize(cols, rows);
            if (this.isConnected && this.ws) {
                this.ws.send(JSON.stringify({
                    type: 'resize',
                    cols: cols,
                    rows: rows
                }));
            }
        });
        
        // Welcome message
        this.showWelcome();
    }
    
    setupEventListeners() {
        // Window resize
        window.addEventListener('resize', () => {
            if (this.fitAddon) {
                setTimeout(() => this.fitAddon.fit(), 100);
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'k':
                        e.preventDefault();
                        this.clearTerminal();
                        break;
                    case 'l':
                        e.preventDefault();
                        this.clearTerminal();
                        break;
                    case '+':
                        e.preventDefault();
                        this.increaseFontSize();
                        break;
                    case '-':
                        e.preventDefault();
                        this.decreaseFontSize();
                        break;
                    case '0':
                        e.preventDefault();
                        this.resetFontSize();
                        break;
                }
            }
            
            // F11 for fullscreen
            if (e.key === 'F11') {
                e.preventDefault();
                this.toggleFullscreen();
            }
        });
        
        // Prevent context menu on terminal
        document.getElementById('terminal').addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });
        
        // Auto-fit on container size changes
        const resizeObserver = new ResizeObserver(() => {
            if (this.fitAddon) {
                this.fitAddon.fit();
            }
        });
        resizeObserver.observe(document.getElementById('terminal'));
    }
    
    connect() {
        if (this.ws) {
            this.ws.close();
        }
        
        this.updateConnectionStatus('connecting', 'Connecting...');
        this.showOverlay('Connecting to terminal...');
        
        // Generate or use existing session ID
        this.sessionId = this.sessionId || this.generateSessionId();
        
        // Connect to WebSocket
        const wsUrl = `ws://${window.location.hostname}:5003/pty/${this.sessionId}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.sessionStartTime = new Date();
            this.updateConnectionStatus('online', 'Connected');
            this.updateSessionId(this.sessionId);
            this.hideOverlay();
            
            this.term.writeln('\x1b[1;32m✓ Terminal connected successfully\x1b[0m');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('offline', 'Connection error');
        };
        
        this.ws.onclose = () => {
            this.isConnected = false;
            this.updateConnectionStatus('offline', 'Disconnected');
            
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                this.term.writeln(`\x1b[1;33m⚠ Connection lost. Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})\x1b[0m`);
                setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
            } else {
                this.term.writeln('\x1b[1;31m✗ Failed to reconnect. Please refresh the page.\x1b[0m');
                this.showOverlay('Connection failed. Please refresh the page.');
            }
        };
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'connected':
                this.sessionId = data.session_id;
                break;
                
            case 'output':
                this.term.write(data.data);
                break;
                
            case 'error':
                this.term.writeln(`\x1b[1;31m✗ Error: ${data.message}\x1b[0m`);
                break;
                
            case 'pong':
                // Handle ping/pong
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    // UI Update Methods
    updateConnectionStatus(status, text) {
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');
        
        statusDot.className = `status-dot ${status}`;
        statusText.textContent = text;
    }
    
    updateSessionId(sessionId) {
        document.getElementById('session-id').textContent = `Session: ${sessionId.substring(0, 8)}...`;
    }
    
    updateTerminalSize(cols, rows) {
        document.getElementById('terminal-size').textContent = `${cols}x${rows}`;
    }
    
    showOverlay(message) {
        const overlay = document.getElementById('terminal-overlay');
        overlay.querySelector('p').textContent = message;
        overlay.style.display = 'flex';
    }
    
    hideOverlay() {
        document.getElementById('terminal-overlay').style.display = 'none';
    }
    
    showWelcome() {
        this.term.writeln('\x1b[1;36m╔══════════════════════════════════════════╗\x1b[0m');
        this.term.writeln('\x1b[1;36m║        🚀 DockerFlow Terminal 🚀         ║\x1b[0m');
        this.term.writeln('\x1b[1;36m║   Claude-Flow & Claude-Code Environment  ║\x1b[0m');
        this.term.writeln('\x1b[1;36m╚══════════════════════════════════════════╝\x1b[0m');
        this.term.writeln('');
        this.term.writeln('Welcome to DockerFlow! Connecting to terminal...');
        this.term.writeln('');
    }
    
    // Control Methods
    clearTerminal() {
        this.term.clear();
    }
    
    newSession() {
        this.sessionId = this.generateSessionId();
        this.connect();
    }
    
    toggleTheme() {
        const body = document.body;
        const themeIcon = document.getElementById('theme-icon');
        
        if (body.classList.contains('dark-theme')) {
            body.classList.remove('dark-theme');
            themeIcon.textContent = '🌙';
            this.applyLightTheme();
        } else {
            body.classList.add('dark-theme');
            themeIcon.textContent = '☀️';
            this.applyDarkTheme();
        }
        
        this.saveSettings();
    }
    
    applyDarkTheme() {
        this.term.options.theme = {
            background: '#0d1117',
            foreground: '#c9d1d9',
            cursor: '#58a6ff',
            selection: '#3392ff44',
            black: '#484f58',
            red: '#ff7b72',
            green: '#3fb950',
            yellow: '#d29922',
            blue: '#58a6ff',
            magenta: '#bc8cff',
            cyan: '#39c5cf',
            white: '#b1bac4'
        };
    }
    
    applyLightTheme() {
        this.term.options.theme = {
            background: '#ffffff',
            foreground: '#24292e',
            cursor: '#0969da',
            selection: '#0969da44',
            black: '#24292e',
            red: '#d1242f',
            green: '#28a745',
            yellow: '#dbab09',
            blue: '#0969da',
            magenta: '#8250df',
            cyan: '#1b7c83',
            white: '#6f7781'
        };
    }
    
    downloadLogs() {
        const logs = [];
        const buffer = this.term.buffer.active;
        
        for (let i = 0; i < buffer.length; i++) {
            const line = buffer.getLine(i);
            if (line) {
                logs.push(line.translateToString(true));
            }
        }
        
        const logContent = logs.join('\n');
        const blob = new Blob([logContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `dockerflow-terminal-${new Date().toISOString()}.log`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        URL.revokeObjectURL(url);
    }
    
    runQuickCommand(command) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify({
                type: 'input',
                data: command + '\n'
            }));
        } else {
            this.term.writeln('\x1b[1;31m✗ Not connected to terminal\x1b[0m');
        }
    }
    
    // Settings Methods
    showSettings() {
        document.getElementById('settings-modal').style.display = 'flex';
        this.populateSettings();
    }
    
    hideSettings() {
        document.getElementById('settings-modal').style.display = 'none';
    }
    
    populateSettings() {
        document.getElementById('font-size').value = this.settings.fontSize;
        document.getElementById('font-size-value').textContent = this.settings.fontSize + 'px';
        document.getElementById('font-family').value = this.settings.fontFamily;
        document.getElementById('cursor-style').value = this.settings.cursorStyle;
        document.getElementById('cursor-blink').checked = this.settings.cursorBlink;
        document.getElementById('bell-sound').checked = this.settings.bellSound;
    }
    
    updateFontSize(size) {
        this.settings.fontSize = parseInt(size);
        this.term.options.fontSize = this.settings.fontSize;
        document.getElementById('font-size-value').textContent = size + 'px';
        this.fitAddon.fit();
        this.saveSettings();
    }
    
    updateFontFamily(family) {
        this.settings.fontFamily = family;
        this.term.options.fontFamily = family;
        this.fitAddon.fit();
        this.saveSettings();
    }
    
    updateCursorStyle(style) {
        this.settings.cursorStyle = style;
        this.term.options.cursorStyle = style;
        this.saveSettings();
    }
    
    updateCursorBlink(blink) {
        this.settings.cursorBlink = blink;
        this.term.options.cursorBlink = blink;
        this.saveSettings();
    }
    
    updateBellSound(enabled) {
        this.settings.bellSound = enabled;
        this.term.options.bellSound = enabled ? 'sound' : 'none';
        this.saveSettings();
    }
    
    increaseFontSize() {
        const newSize = Math.min(this.settings.fontSize + 2, 24);
        this.updateFontSize(newSize);
    }
    
    decreaseFontSize() {
        const newSize = Math.max(this.settings.fontSize - 2, 10);
        this.updateFontSize(newSize);
    }
    
    resetFontSize() {
        this.updateFontSize(14);
    }
    
    loadSettings() {
        const defaultSettings = {
            fontSize: 14,
            fontFamily: "'Cascadia Code', 'Menlo', 'Monaco', 'Courier New', monospace",
            cursorStyle: 'block',
            cursorBlink: true,
            bellSound: false,
            theme: 'dark'
        };
        
        try {
            const saved = localStorage.getItem('dockerflow-terminal-settings');
            return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
        } catch (e) {
            return defaultSettings;
        }
    }
    
    saveSettings() {
        try {
            localStorage.setItem('dockerflow-terminal-settings', JSON.stringify(this.settings));
        } catch (e) {
            console.error('Failed to save settings:', e);
        }
    }
    
    applySettings() {
        if (this.settings.theme === 'light') {
            document.body.classList.remove('dark-theme');
            document.getElementById('theme-icon').textContent = '🌙';
        } else {
            document.body.classList.add('dark-theme');
            document.getElementById('theme-icon').textContent = '☀️';
        }
    }
    
    // Utility Methods
    generateSessionId() {
        return 'term_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    
    startUptimeCounter() {
        this.uptimeInterval = setInterval(() => {
            if (this.sessionStartTime) {
                const now = new Date();
                const diff = now - this.sessionStartTime;
                const minutes = Math.floor(diff / 60000);
                const seconds = Math.floor((diff % 60000) / 1000);
                document.getElementById('session-uptime').textContent = 
                    `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
    
    // Send ping to keep connection alive
    startPingInterval() {
        setInterval(() => {
            if (this.isConnected && this.ws) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }
}

// Global functions for HTML onclick handlers
window.newSession = () => terminal.newSession();
window.clearTerminal = () => terminal.clearTerminal();
window.toggleTheme = () => terminal.toggleTheme();
window.downloadLogs = () => terminal.downloadLogs();
window.showSettings = () => terminal.showSettings();
window.hideSettings = () => terminal.hideSettings();
window.runQuickCommand = (cmd) => terminal.runQuickCommand(cmd);
window.updateFontSize = (size) => terminal.updateFontSize(size);
window.updateFontFamily = (family) => terminal.updateFontFamily(family);
window.updateCursorStyle = (style) => terminal.updateCursorStyle(style);
window.updateCursorBlink = (blink) => terminal.updateCursorBlink(blink);
window.updateBellSound = (enabled) => terminal.updateBellSound(enabled);

// Initialize terminal when page loads
let terminal;
document.addEventListener('DOMContentLoaded', () => {
    terminal = new DockerFlowTerminal();
});