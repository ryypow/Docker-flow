#!/usr/bin/env python3
"""
DockerFlow API Test Suite
Comprehensive tests for all REST API endpoints
"""

import pytest
import requests
import json
import time
import subprocess
import os
import tempfile
from typing import Dict, Any
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:5002"
TIMEOUT = 30
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2

class TestAPIEndpoints:
    """Test all API endpoints"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.session = requests.Session()
        cls.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Wait for API to be ready
        cls.wait_for_api()
    
    @classmethod
    def wait_for_api(cls, max_attempts: int = 10):
        """Wait for API server to be ready"""
        for attempt in range(max_attempts):
            try:
                response = cls.session.get(f"{BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    print(f"API server ready after {attempt + 1} attempts")
                    return
            except requests.exceptions.RequestException:
                pass
            
            if attempt < max_attempts - 1:
                print(f"API not ready, attempt {attempt + 1}/{max_attempts}, waiting...")
                time.sleep(2)
        
        raise Exception("API server did not become ready within timeout")
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.session.get(f"{BASE_URL}/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data
        assert data["name"] == "DockerFlow API"
        assert data["version"] == "2.0.0"
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.session.get(f"{BASE_URL}/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"
    
    def test_status_endpoint(self):
        """Test system status endpoint"""
        response = self.session.get(f"{BASE_URL}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ok" in data
        assert "system" in data
        assert "environment" in data
        assert "timestamp" in data
        
        # Check system info
        system = data["system"]
        assert "node" in system
        assert "npm" in system
        assert "python" in system
        assert "claude_flow" in system
        assert "cwd" in system
        assert "user" in system
        assert "home" in system
    
    def test_info_endpoint(self):
        """Test claude-flow info endpoint"""
        response = self.session.get(f"{BASE_URL}/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "claude_flow" in data
        assert "sparc_modes" in data
        
        # Check claude-flow info
        cf_info = data["claude_flow"]
        assert "version" in cf_info
        assert "commands" in cf_info
        
        # Check SPARC modes
        modes = data["sparc_modes"]
        expected_modes = [
            "spec-pseudocode", "architect", "code", "tdd",
            "debug", "security-review", "docs-writer", "integration"
        ]
        for mode in expected_modes:
            assert mode in modes
    
    def test_commands_endpoint(self):
        """Test available commands endpoint"""
        response = self.session.get(f"{BASE_URL}/commands")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "commands" in data
        commands = data["commands"]
        
        # Check command categories
        categories = [cmd["category"] for cmd in commands]
        assert "Core" in categories
        assert "SPARC" in categories
        assert "Swarm" in categories
        
        # Check command structure
        for category_data in commands:
            assert "category" in category_data
            assert "commands" in category_data
            for cmd in category_data["commands"]:
                assert "cmd" in cmd
                assert "desc" in cmd
    
    def test_run_command_basic(self):
        """Test basic command execution"""
        payload = {
            "cmd": "echo 'Hello DockerFlow'",
            "cwd": "/workspace",
            "timeout": 10
        }
        
        response = self.session.post(f"{BASE_URL}/run", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ok" in data
        assert "cmd" in data
        assert "output" in data
        assert "exit_code" in data
        assert "timestamp" in data
        
        assert data["ok"] is True
        assert data["cmd"] == payload["cmd"]
        assert "Hello DockerFlow" in data["output"]
        assert data["exit_code"] == 0
    
    def test_run_command_with_error(self):
        """Test command execution with error"""
        payload = {
            "cmd": "nonexistent-command",
            "cwd": "/workspace",
            "timeout": 10
        }
        
        response = self.session.post(f"{BASE_URL}/run", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ok" in data
        assert "cmd" in data
        assert "output" in data
        assert "exit_code" in data
        
        assert data["ok"] is False
        assert data["exit_code"] != 0
    
    def test_run_command_timeout(self):
        """Test command timeout"""
        payload = {
            "cmd": "sleep 5",
            "cwd": "/workspace",
            "timeout": 2  # Shorter than sleep duration
        }
        
        response = self.session.post(f"{BASE_URL}/run", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ok" in data
        assert "error" in data
        assert data["ok"] is False
        assert "timed out" in data["error"].lower()
    
    def test_run_command_security(self):
        """Test security restrictions"""
        dangerous_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1"
        ]
        
        for cmd in dangerous_commands:
            payload = {
                "cmd": cmd,
                "cwd": "/workspace"
            }
            
            response = self.session.post(f"{BASE_URL}/run", json=payload)
            
            assert response.status_code == 403  # Forbidden
    
    def test_run_command_missing_cmd(self):
        """Test command execution without cmd parameter"""
        payload = {
            "cwd": "/workspace"
        }
        
        response = self.session.post(f"{BASE_URL}/run", json=payload)
        
        assert response.status_code == 400
    
    def test_claude_flow_version(self):
        """Test claude-flow version command"""
        payload = {
            "cmd": "npx claude-flow --version",
            "cwd": "/workspace",
            "timeout": 30
        }
        
        response = self.session.post(f"{BASE_URL}/run", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] is True
        assert data["exit_code"] == 0
        # Should contain version info in output
        assert len(data["output"].strip()) > 0
    
    def test_claude_flow_help(self):
        """Test claude-flow help command"""
        payload = {
            "cmd": "npx claude-flow --help",
            "cwd": "/workspace",
            "timeout": 30
        }
        
        response = self.session.post(f"{BASE_URL}/run", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] is True
        assert data["exit_code"] == 0
        # Should contain help text
        output = data["output"].lower()
        assert "usage" in output or "commands" in output or "options" in output
    
    def test_async_command_execution(self):
        """Test asynchronous command execution"""
        payload = {
            "cmd": "echo 'Async test' && sleep 2 && echo 'Done'",
            "cwd": "/workspace"
        }
        
        # Start async execution
        response = self.session.post(f"{BASE_URL}/execute-async", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "task_id" in data
        assert "status" in data
        assert "cmd" in data
        assert data["status"] == "started"
        
        task_id = data["task_id"]
        
        # Check task status
        max_attempts = 10
        for attempt in range(max_attempts):
            response = self.session.get(f"{BASE_URL}/task/{task_id}")
            assert response.status_code == 200
            
            task_data = response.json()
            assert "status" in task_data
            
            if task_data["status"] == "completed":
                assert "output" in task_data
                assert "exit_code" in task_data
                assert "Async test" in task_data["output"]
                assert "Done" in task_data["output"]
                break
            elif task_data["status"] == "error":
                pytest.fail(f"Task failed with error: {task_data.get('error', 'Unknown error')}")
            
            if attempt < max_attempts - 1:
                time.sleep(1)
        else:
            pytest.fail("Async task did not complete within timeout")
    
    def test_task_not_found(self):
        """Test getting status of non-existent task"""
        response = self.session.get(f"{BASE_URL}/task/nonexistent-task-id")
        
        assert response.status_code == 404

class TestAPIPerformance:
    """Performance tests for API endpoints"""
    
    @classmethod
    def setup_class(cls):
        cls.session = requests.Session()
        cls.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def test_health_endpoint_performance(self):
        """Test health endpoint response time"""
        start_time = time.time()
        response = self.session.get(f"{BASE_URL}/health")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import queue
        
        results = queue.Queue()
        num_threads = 10
        
        def make_request():
            try:
                response = self.session.get(f"{BASE_URL}/health")
                results.put((response.status_code, response.elapsed.total_seconds()))
            except Exception as e:
                results.put((None, str(e)))
        
        threads = []
        start_time = time.time()
        
        # Start all threads
        for _ in range(num_threads):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Check results
        success_count = 0
        total_response_time = 0
        
        while not results.empty():
            status_code, response_time = results.get()
            if status_code == 200:
                success_count += 1
                total_response_time += float(response_time)
        
        assert success_count == num_threads
        avg_response_time = total_response_time / success_count
        total_time = end_time - start_time
        
        # All requests should complete reasonably fast
        assert avg_response_time < 2.0
        assert total_time < 5.0

class TestAPIIntegration:
    """Integration tests with actual claude-flow commands"""
    
    @classmethod
    def setup_class(cls):
        cls.session = requests.Session()
        cls.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def test_claude_flow_scan(self):
        """Test claude-flow scan command"""
        payload = {
            "cmd": "npx claude-flow scan",
            "cwd": "/workspace",
            "timeout": 60
        }
        
        response = self.session.post(f"{BASE_URL}/run", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Command should complete (may succeed or fail based on environment)
        assert "exit_code" in data
        assert "output" in data
    
    def test_claude_flow_sparc_modes(self):
        """Test claude-flow SPARC modes command"""
        payload = {
            "cmd": "npx claude-flow sparc modes",
            "cwd": "/workspace",
            "timeout": 60
        }
        
        response = self.session.post(f"{BASE_URL}/run", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should list available SPARC modes
        if data["ok"]:
            output = data["output"].lower()
            # Check for some expected modes
            expected_modes = ["architect", "code", "tdd"]
            mode_found = any(mode in output for mode in expected_modes)
            assert mode_found, f"No expected SPARC modes found in output: {data['output']}"

def run_tests():
    """Run all tests"""
    print("Starting DockerFlow API Test Suite...")
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
        "--durations=10"
    ])
    
    return exit_code

if __name__ == "__main__":
    import sys
    sys.exit(run_tests())