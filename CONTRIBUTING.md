# Contributing to DockerFlow

First off, thank you for considering contributing to DockerFlow! It's people like you that make DockerFlow such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title** for the issue to identify the problem
* **Describe the exact steps** which reproduce the problem
* **Provide specific examples** to demonstrate the steps
* **Describe the behavior** you observed after following the steps
* **Explain which behavior** you expected to see instead and why
* **Include screenshots** if possible
* **Include your environment details** (OS, Docker version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title** for the issue
* **Provide a step-by-step description** of the suggested enhancement
* **Provide specific examples** to demonstrate the steps
* **Describe the current behavior** and explain which behavior you expected to see instead
* **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the existing style
6. Issue that pull request!

## Development Process

### Setting Up Your Development Environment

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/your-username/dockerflow.git
   cd dockerflow
   ```

2. Copy the environment template:
   ```bash
   cp .env.example .env
   # Add your API keys
   ```

3. Build the Docker image:
   ```bash
   docker compose build
   ```

4. Run the tests:
   ```bash
   ./scripts/test.sh
   ```

### Testing

* Write tests for any new functionality
* Ensure all tests pass before submitting PR
* Include integration tests for API changes
* Test both Python and JavaScript components

### Code Style

#### Python
* Follow PEP 8
* Use type hints where appropriate
* Add docstrings to all functions and classes
* Run `black` for formatting
* Run `flake8` for linting

#### JavaScript
* Use ES6+ features
* Follow existing code style
* Add JSDoc comments for functions
* Run `prettier` for formatting
* Run `eslint` for linting

#### Docker
* Keep images small and efficient
* Use multi-stage builds when appropriate
* Pin versions for reproducibility
* Follow Docker best practices

### Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line
* Consider using conventional commits format:
  * `feat:` for new features
  * `fix:` for bug fixes
  * `docs:` for documentation
  * `style:` for formatting
  * `refactor:` for code refactoring
  * `test:` for tests
  * `chore:` for maintenance

### Documentation

* Update README.md with details of changes to the interface
* Update documentation for API changes
* Add inline comments for complex logic
* Update CHANGELOG.md following Keep a Changelog format

## Project Structure

```
dockerflow/
├── server/           # Python backend
├── ui/              # Frontend files
├── tests/           # Test suite
├── docs/            # Documentation
├── scripts/         # Utility scripts
├── .github/         # GitHub specific files
└── config/          # Configuration files
```

## Release Process

1. Update version in relevant files
2. Update CHANGELOG.md
3. Create a pull request
4. After merge, tag the release
5. Build and push Docker images
6. Update release notes

## Questions?

Feel free to open an issue with your question or reach out to the maintainers directly.

Thank you for contributing! 🚀