# Contributing to SpectraChirp

First off, thank you for considering contributing to SpectraChirp! We welcome any contributions that improve the project.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs
If you find a bug, please open an issue on our [GitHub Issue Tracker](https://github.com/saas-erp-hub/SpectraChirp/issues). 
- Use the "Bug Report" template.
- Provide a clear title and a detailed description of the issue, including steps to reproduce it.

### Suggesting Enhancements
If you have an idea for a new feature, please open an issue using the "Feature Request" template to start a discussion.

### Pull Requests
We actively welcome your pull requests.

1.  **Fork the Repository** and create your branch from `main`.
2.  **Set up your development environment** (see below).
3.  **Make your changes.** Ensure your code adheres to the project's style.
4.  **Add tests** for your new feature or bug fix.
5.  **Ensure all tests pass** by running `pytest` in the `backend` directory.
6.  **Write clear commit messages.** We follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.
7.  **Create a Pull Request** targeting the `main` branch. Please link the PR to any relevant issues.

## Development Setup

1.  **Fork and clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/SpectraChirp.git
    cd SpectraChirp
    ```

2.  **Install dependencies:**
    This project uses `uv` for package management.
    ```bash
    uv pip install -r backend/requirements.txt
    ```

## Running Tests

To ensure your changes haven't broken anything, run the full test suite:
```bash
# Navigate to the backend directory
cd backend

# Run pytest
pytest
```

Thank you for your contribution!
