# Contributing to Eye Communication System

We love your input! We want to make contributing to the Eye Communication System as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Pull Requests

### Process
1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

### Any contributions you make will be under the MIT Software License
In submitting a pull request, you agree to license your contributions under the MIT License.

### In short
- Fork the project
- Create a feature branch
- Make your changes
- Add tests for your changes
- Ensure all tests pass
- Submit a pull request

## Coding Standards

### Python Code Style
- Follow PEP 8 guidelines
- Use 4 spaces for indentation
- Maximum line length: 88 characters
- Use f-strings for string formatting
- Add type hints where appropriate

### Documentation
- Add docstrings to all functions and classes
- Use Google-style docstrings
- Include parameter types and return types
- Add examples for complex functions

### Error Handling
- Always handle potential exceptions
- Use specific exception types
- Include meaningful error messages
- Log errors appropriately

## Testing

### Running Tests
```bash
python -m pytest tests/
```

### Test Coverage
We aim for >80% test coverage. You can check coverage with:
```bash
python -m pytest --cov=eye_comm_system tests/
```

### Writing Tests
- Test both success and failure cases
- Use descriptive test names
- Mock external dependencies
- Test edge cases and boundary conditions

## Project Structure

```
eye_comm_system/
├── main.py              # Main application entry point
├── eye_tracker.py       # Eye tracking module
├── tts.py              # Text-to-speech module
├── requirements.txt     # Dependencies
├── README.md           # Project documentation
├── LICENSE             # MIT License
├── .gitignore          # Git ignore file
├── CONTRIBUTING.md     # This file
├── tests/              # Test suite
│   ├── test_eye_tracker.py
│   ├── test_tts.py
│   └── test_main.py
└── docs/               # Additional documentation
    ├── API.md
    └── USAGE.md
```

## Types of Contributions

### Bug Reports
- Use the GitHub issue tracker
- Include system information
- Provide steps to reproduce
- Add screenshots if applicable
- Include error logs

### Feature Requests
- Use the GitHub issue tracker
- Describe the feature clearly
- Explain the use case
- Consider implementation complexity

### Code Contributions
- Bug fixes
- New features
- Performance improvements
- Documentation improvements
- Test improvements

## Development Environment Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/eye-communication-system.git
cd eye-communication-system
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

4. **Run tests**
```bash
python -m pytest
```

5. **Run code formatting**
```bash
black .
isort .
```

## Code Review Process

### What We Look For
- Code follows style guidelines
- Tests are included and passing
- Documentation is updated
- Performance impact is considered
- Security implications are considered

### Review Guidelines
- Be constructive and respectful
- Focus on code, not the person
- Provide specific suggestions
- Ask questions if unclear

## Release Process

1. Update version number in `main.py`
2. Update `CHANGELOG.md`
3. Create a new release on GitHub
4. Tag the release with version number

## Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Welcome newcomers
- Focus on what is best for the community
- Show empathy towards other community members

### Getting Help
- Check the documentation first
- Search existing issues
- Ask questions in GitHub discussions
- Join our community chat (if available)

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to the Eye Communication System! 🎯
