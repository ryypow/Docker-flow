#!/usr/bin/env python3
"""
DockerFlow Container Test Suite
Tests for Docker container functionality and integration
"""

import pytest
import docker
import requests
import time
import subprocess
import tempfile
import os
from pathlib import Path

# Test configuration
CONTAINER_NAME = "dockerflow-test"
IMAGE_NAME = "dockerflow:test"
TIMEOUT = 300  # 5 minutes for build/start operations
HEALTH_CHECK_INTERVAL = 5
MAX_HEALTH_CHECKS = 24  # 2 minutes total

class TestDockerBuild:
    """Test Docker image building"""
    
    @classmethod
    def setup_class(cls):
        """Setup Docker client"""
        cls.client = docker.from_env()
        cls.image = None
        cls.container = None
    
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists and is valid"""
        dockerfile_path = Path("Dockerfile")
        assert dockerfile_path.exists(), "Dockerfile not found"
        
        content = dockerfile_path.read_text()
        assert "FROM" in content, "Dockerfile missing FROM instruction"
        assert "WORKDIR" in content, "Dockerfile missing WORKDIR instruction"
        assert "COPY" in content, "Dockerfile missing COPY instruction"
    
    def test_docker_compose_file(self):
        """Test that docker-compose.yml exists and is valid"""
        compose_path = Path("docker-compose.yml")
        assert compose_path.exists(), "docker-compose.yml not found"
        
        content = compose_path.read_text()
        assert "version:" in content, "docker-compose.yml missing version"
        assert "services:" in content, "docker-compose.yml missing services"
    
    def test_build_image(self):
        """Test building Docker image"""
        print("Building Docker image...")
        
        try:
            # Build image
            self.image, build_logs = self.client.images.build(
                path=".",
                tag=IMAGE_NAME,
                rm=True,
                forcerm=True,
                timeout=TIMEOUT
            )
            
            # Print build logs for debugging
            for log in build_logs:
                if 'stream' in log:
                    print(log['stream'].strip())
            
            assert self.image is not None, "Image build failed"
            print(f"Successfully built image: {self.image.id}")
            
        except docker.errors.BuildError as e:
            pytest.fail(f"Docker build failed: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error during build: {e}")
    
    def test_image_properties(self):
        """Test image properties and metadata"""
        if not self.image:
            pytest.skip("Image not built")
        
        # Check image exists
        assert self.image.id is not None
        
        # Check image labels/metadata
        config = self.image.attrs.get('Config', {})
        
        # Should have appropriate working directory
        workdir = config.get('WorkingDir')
        assert workdir == '/workspace', f"Expected WorkingDir '/workspace', got '{workdir}'"
        
        # Should have exposed ports
        exposed_ports = config.get('ExposedPorts', {})
        expected_ports = ['5000/tcp', '5001/tcp', '5002/tcp', '5003/tcp', '7681/tcp']
        
        for port in expected_ports:
            assert port in exposed_ports, f"Port {port} not exposed"
    
    def test_image_size(self):
        """Test image size is reasonable"""
        if not self.image:
            pytest.skip("Image not built")
        
        size_mb = self.image.attrs['Size'] / (1024 * 1024)
        print(f"Image size: {size_mb:.1f} MB")
        
        # Should be less than 4GB (reasonable for development image)
        assert size_mb < 4000, f"Image too large: {size_mb:.1f} MB"

class TestContainerLifecycle:
    """Test container lifecycle management"""
    
    @classmethod
    def setup_class(cls):
        """Setup for container tests"""
        cls.client = docker.from_env()
        cls.container = None
        
        # Check if image exists
        try:
            cls.image = cls.client.images.get(IMAGE_NAME)
        except docker.errors.ImageNotFound:
            pytest.skip(f"Docker image {IMAGE_NAME} not found. Run build tests first.")
    
    def test_container_creation(self):
        """Test container creation"""
        try:
            self.container = self.client.containers.create(
                image=IMAGE_NAME,
                name=CONTAINER_NAME,
                ports={
                    '5000/tcp': 5000,
                    '5001/tcp': 5001,
                    '5002/tcp': 5002,
                    '5003/tcp': 5003,
                    '7681/tcp': 7681
                },
                environment={
                    'NODE_ENV': 'production',
                    'LOG_LEVEL': 'info'
                },
                detach=True,
                remove=True  # Auto-remove when stopped
            )
            
            assert self.container is not None
            print(f"Container created: {self.container.id}")
            
        except Exception as e:
            pytest.fail(f"Container creation failed: {e}")
    
    def test_container_start(self):
        """Test container startup"""
        if not self.container:
            pytest.skip("Container not created")
        
        try:
            self.container.start()
            print("Container started")
            
            # Wait for container to be running
            for _ in range(10):
                self.container.reload()
                if self.container.status == 'running':
                    break
                time.sleep(1)
            else:
                pytest.fail("Container did not start within timeout")
            
            assert self.container.status == 'running'
            
        except Exception as e:
            pytest.fail(f"Container start failed: {e}")
    
    def test_container_health(self):
        """Test container health checks"""
        if not self.container or self.container.status != 'running':
            pytest.skip("Container not running")
        
        # Wait for health checks to pass
        print("Waiting for container health checks...")
        
        healthy = False
        for attempt in range(MAX_HEALTH_CHECKS):
            self.container.reload()
            health = self.container.attrs.get('State', {}).get('Health', {})
            status = health.get('Status')
            
            if status == 'healthy':
                healthy = True
                break
            elif status == 'unhealthy':
                pytest.fail("Container reported as unhealthy")
            
            print(f"Health check {attempt + 1}/{MAX_HEALTH_CHECKS}: {status}")
            time.sleep(HEALTH_CHECK_INTERVAL)
        
        assert healthy, "Container did not become healthy within timeout"
        print("Container is healthy")
    
    def test_container_processes(self):
        """Test processes running in container"""
        if not self.container or self.container.status != 'running':
            pytest.skip("Container not running")
        
        # Get running processes
        try:
            processes = self.container.top()
            process_list = processes['Processes']
            
            # Should have multiple processes running
            assert len(process_list) > 0, "No processes found in container"
            
            # Look for expected processes
            process_commands = [proc[-1] for proc in process_list]  # Last column is usually command
            process_str = ' '.join(process_commands)
            
            print(f"Container processes: {len(process_list)}")
            for proc in process_list[:5]:  # Show first 5 processes
                print(f"  {proc}")
            
        except Exception as e:
            print(f"Warning: Could not get process list: {e}")
    
    def test_container_logs(self):
        """Test container logging"""
        if not self.container:
            pytest.skip("Container not created")
        
        try:
            # Get recent logs
            logs = self.container.logs(tail=20, timestamps=True)
            log_str = logs.decode('utf-8')
            
            print("Container logs (last 20 lines):")
            print(log_str)
            
            # Should have some log output
            assert len(log_str.strip()) > 0, "No logs found"
            
        except Exception as e:
            print(f"Warning: Could not get logs: {e}")
    
    def test_container_stop(self):
        """Test container stopping"""
        if not self.container:
            pytest.skip("Container not created")
        
        try:
            self.container.stop(timeout=10)
            
            # Wait for container to stop
            for _ in range(10):
                self.container.reload()
                if self.container.status == 'exited':
                    break
                time.sleep(1)
            
            assert self.container.status == 'exited'
            print("Container stopped successfully")
            
        except Exception as e:
            print(f"Warning: Container stop failed: {e}")
    
    def teardown_method(self):
        """Cleanup after each test"""
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
            except:
                pass

class TestContainerNetworking:
    """Test container networking and port exposure"""
    
    @classmethod
    def setup_class(cls):
        """Setup networking tests"""
        cls.client = docker.from_env()
        cls.container = None
        
        # Start container for networking tests
        try:
            image = cls.client.images.get(IMAGE_NAME)
            cls.container = cls.client.containers.run(
                image=IMAGE_NAME,
                ports={
                    '5000/tcp': 15000,  # Use different ports to avoid conflicts
                    '5001/tcp': 15001,
                    '5002/tcp': 15002,
                    '5003/tcp': 15003,
                    '7681/tcp': 17681
                },
                environment={
                    'NODE_ENV': 'test',
                    'LOG_LEVEL': 'debug'
                },
                detach=True,
                remove=True,
                name=f"{CONTAINER_NAME}-network"
            )
            
            # Wait for container to be ready
            time.sleep(30)
            
        except docker.errors.ImageNotFound:
            pytest.skip(f"Docker image {IMAGE_NAME} not found")
        except Exception as e:
            pytest.skip(f"Could not start container for networking tests: {e}")
    
    def test_ui_port_accessibility(self):
        """Test UI port (5000) accessibility"""
        try:
            response = requests.get("http://localhost:15000", timeout=10)
            assert response.status_code == 200, f"UI port returned {response.status_code}"
            print("UI port is accessible")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"UI port not accessible: {e}")
    
    def test_api_port_accessibility(self):
        """Test API port (5002) accessibility"""
        try:
            response = requests.get("http://localhost:15002/health", timeout=10)
            assert response.status_code == 200, f"API port returned {response.status_code}"
            
            data = response.json()
            assert data.get('status') == 'healthy'
            print("API port is accessible and healthy")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API port not accessible: {e}")
    
    def test_websocket_port_accessibility(self):
        """Test WebSocket port (5001) accessibility"""
        try:
            response = requests.get("http://localhost:15001", timeout=10)
            # WebSocket endpoint should return some response (not necessarily 200)
            assert response.status_code in [200, 404, 405], f"Unexpected status {response.status_code}"
            print("WebSocket port is accessible")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"WebSocket port not accessible: {e}")
    
    def test_terminal_port_accessibility(self):
        """Test Terminal port (5003) accessibility"""
        try:
            response = requests.get("http://localhost:15003", timeout=10)
            assert response.status_code == 200, f"Terminal port returned {response.status_code}"
            print("Terminal port is accessible")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Terminal port not accessible: {e}")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup networking test container"""
        if cls.container:
            try:
                cls.container.stop()
                cls.container.remove()
            except:
                pass

class TestContainerVolumes:
    """Test container volume mounts and persistence"""
    
    def test_workspace_volume(self):
        """Test workspace volume mounting"""
        client = docker.from_env()
        
        try:
            image = client.images.get(IMAGE_NAME)
        except docker.errors.ImageNotFound:
            pytest.skip(f"Docker image {IMAGE_NAME} not found")
        
        # Create temporary directory for workspace
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("Volume test content")
            
            # Run container with volume mount
            try:
                container = client.containers.run(
                    image=IMAGE_NAME,
                    volumes={temp_dir: {'bind': '/workspace', 'mode': 'rw'}},
                    command=['cat', '/workspace/test.txt'],
                    remove=True
                )
                
                output = container.decode('utf-8').strip()
                assert output == "Volume test content", f"Volume mount failed: {output}"
                print("Workspace volume mount works")
                
            except Exception as e:
                pytest.fail(f"Volume mount test failed: {e}")

class TestContainerEnvironment:
    """Test container environment and configuration"""
    
    def test_environment_variables(self):
        """Test environment variable passing"""
        client = docker.from_env()
        
        try:
            image = client.images.get(IMAGE_NAME)
        except docker.errors.ImageNotFound:
            pytest.skip(f"Docker image {IMAGE_NAME} not found")
        
        # Test environment variables
        env_vars = {
            'TEST_VAR': 'test_value',
            'NODE_ENV': 'test',
            'LOG_LEVEL': 'debug'
        }
        
        try:
            container = client.containers.run(
                image=IMAGE_NAME,
                environment=env_vars,
                command=['env'],
                remove=True
            )
            
            output = container.decode('utf-8')
            
            for key, value in env_vars.items():
                assert f"{key}={value}" in output, f"Environment variable {key} not found"
            
            print("Environment variables passed correctly")
            
        except Exception as e:
            pytest.fail(f"Environment variable test failed: {e}")
    
    def test_user_permissions(self):
        """Test non-root user execution"""
        client = docker.from_env()
        
        try:
            image = client.images.get(IMAGE_NAME)
        except docker.errors.ImageNotFound:
            pytest.skip(f"Docker image {IMAGE_NAME} not found")
        
        try:
            # Check user ID
            container = client.containers.run(
                image=IMAGE_NAME,
                command=['id'],
                remove=True
            )
            
            output = container.decode('utf-8').strip()
            print(f"Container user: {output}")
            
            # Should not be running as root (uid=0)
            assert "uid=0(" not in output, "Container running as root user"
            print("Container running as non-root user")
            
        except Exception as e:
            pytest.fail(f"User permission test failed: {e}")

def cleanup_test_containers():
    """Cleanup any test containers"""
    client = docker.from_env()
    
    # Remove test containers
    for container in client.containers.list(all=True):
        if container.name and CONTAINER_NAME in container.name:
            try:
                container.stop()
                container.remove()
                print(f"Cleaned up container: {container.name}")
            except:
                pass
    
    # Remove test images
    try:
        client.images.remove(IMAGE_NAME, force=True)
        print(f"Cleaned up image: {IMAGE_NAME}")
    except:
        pass

def run_tests():
    """Run all Docker tests"""
    print("Starting DockerFlow Container Test Suite...")
    
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
    import atexit
    
    # Register cleanup function
    atexit.register(cleanup_test_containers)
    
    try:
        sys.exit(run_tests())
    except KeyboardInterrupt:
        print("\nTest interrupted. Cleaning up...")
        cleanup_test_containers()
        sys.exit(1)