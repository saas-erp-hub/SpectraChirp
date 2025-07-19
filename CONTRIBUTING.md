# Contributing to SpectraChirp

We welcome contributions to SpectraChirp! To ensure a smooth and collaborative process, please follow these guidelines.

## How to Contribute

1.  **Fork the Repository**: Start by forking the `SpectraChirp` repository to your GitHub account.

2.  **Clone Your Fork**: Clone your forked repository to your local machine:
    ```bash
    git clone https://github.com/your-username/SpectraChirp.git
    cd SpectraChirp
    ```

3.  **Create a New Branch**: For each new feature, bug fix, or significant change, create a new branch. Use a descriptive name for your branch (e.g., `feature/add-new-modem`, `bugfix/fix-decode-error`).
    ```bash
    git checkout -b feature/your-feature-name
    ```

4.  **Make Your Changes**: Implement your changes, ensuring they adhere to the project's [Code Quality](#code-quality) and [Code Style](#code-style) guidelines (see `backend/GEMINI.md` for details).

5.  **Write Tests**: New features and bug fixes should be accompanied by appropriate tests. Ensure all existing tests pass.
    ```bash
    uv run pytest
    ```

6.  **Commit Your Changes**: Write clear, concise commit messages that explain *what* you did and *why*. Follow the [Commit Message Guidelines](#commit-message-guidelines) (see `backend/GEMINI.md`).
    ```bash
    git add .
    git commit -m "feat: Add new feature"
    ```

7.  **Push to Your Fork**: Push your new branch and commits to your forked repository on GitHub.
    ```bash
    git push origin feature/your-feature-name
    ```

8.  **Create a Pull Request (PR)**: Once your changes are pushed, go to your forked repository on GitHub and create a new Pull Request targeting the `main` branch of the original `SpectraChirp` repository. Provide a clear description of your changes.

## Code Quality and Style

Refer to the `backend/GEMINI.md` file for detailed guidelines on code quality, style, and testing requirements.

## Reporting Bugs

If you find a bug, please open an issue on the [GitHub Issue Tracker](https://github.com/saas-erp-hub/SpectraChirp/issues). Provide as much detail as possible, including steps to reproduce the bug, expected behavior, and actual behavior.

## Feature Requests

If you have an idea for a new feature, please open an issue on the [GitHub Issue Tracker](https://github.com/saas-erp-hub/SpectraChirp/issues) to discuss it before starting any development. This helps ensure that your idea aligns with the project's goals and avoids duplicate work.

## Questions

If you have questions about using SpectraChirp or contributing, feel free to open an issue or reach out to the maintainers.
