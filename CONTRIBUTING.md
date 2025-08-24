# CONTRIBUTING.md

How to contribute

## Types of changes for pull requests and commits

- feat: A new feature
- fix: A bug fix
- chore: Routine tasks, maintenance, or tooling changes
- docs: Documentation updates
- style: Code style changes (e.g., formatting, indentation)
- refactor: Code refactoring without changes in functionality
- test: Adding or modifying tests
- perf: Performance improvements
- ci: Changes to the CI/CD configuration or scripts
- other: Other changes that don't fit into the above categories

## Making Pull Requests

1. Create a new branch from `main` for your changes:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them following the commit message format:

   ```
   type: brief description of changes
   ```

   Example: `feat: add user authentication`

3. Push your branch to the remote repository:

   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request (PR) on GitHub:
   - Go to the repository on GitHub
   - Click "Compare & pull request"
   - Fill in the PR description following the template
   - Request reviews from relevant team members
   - **Important**: We use "Rebase and merge" as our default merge strategy. Please ensure your branch is up to date with main before merging.

## Branch Management

After your PR is approved and merged:

1. Switch back to main branch:

   ```bash
   git checkout main
   git pull origin main
   ```

2. Delete your feature branch locally:

   ```bash
   git branch -d feature/your-feature-name
   ```

3. Delete the remote branch:

   ```bash
   git push origin --delete feature/your-feature-name
   ```

**Important**: Since we use "Rebase and merge" as our default strategy:

- Always ensure your branch is up to date with main before merging
- After merging, your commits will be rebased on top of main
- This keeps our git history clean and linear
- Make sure to pull the latest changes from main before deleting your branch
