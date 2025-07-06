# Git Workflow and Branching Strategy

## Overview

This document outlines the Git workflow and branching strategy for the AI Trading Platform project.

## Branching Strategy

We use a **Git Flow** inspired strategy with the following branch structure:

### Main Branches

- **`main`** - Production-ready code
  - Always deployable
  - Protected branch requiring PR reviews
  - Automatically deployed to production

- **`develop`** - Integration branch for features
  - Latest development changes
  - Base branch for feature development
  - Deployed to staging environment

### Supporting Branches

- **`feature/*`** - Feature development
  - Created from `develop`
  - Merged back to `develop` via PR
  - Examples: `feature/stock-search`, `feature/ml-ensemble`

- **`hotfix/*`** - Production bug fixes
  - Created from `main`
  - Merged to both `main` and `develop`
  - Examples: `hotfix/security-patch`, `hotfix/trading-bug`

- **`release/*`** - Prepare releases
  - Created from `develop`
  - Only bug fixes and release preparation
  - Merged to `main` and `develop`

## Workflow Process

### 1. Feature Development

```bash
# Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/new-feature-name

# Work on feature
git add .
git commit -m "feat: implement new feature"

# Push and create PR
git push origin feature/new-feature-name
# Create Pull Request to develop branch
```

### 2. Release Process

```bash
# Create release branch
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# Prepare release (version bumps, changelog)
git add .
git commit -m "chore: prepare release v1.2.0"

# Create PR to main
git push origin release/v1.2.0
# Create Pull Request to main branch
```

### 3. Hotfix Process

```bash
# Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix

# Fix the issue
git add .
git commit -m "fix: resolve critical trading bug"

# Push and create PRs to both main and develop
git push origin hotfix/critical-bug-fix
```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic changes)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Build process or auxiliary tool changes
- **ci**: CI/CD configuration changes
- **perf**: Performance improvements
- **security**: Security improvements

### Examples
```bash
feat(trading): add ensemble ML prediction system
fix(auth): resolve JWT token expiration issue
docs(api): update trading endpoints documentation
chore(deps): update Python dependencies
ci(deploy): add production deployment pipeline
```

## Pull Request Guidelines

### Requirements
- All PRs must pass CI/CD checks
- Code review required from at least 1 team member
- All tests must pass
- No merge conflicts
- Documentation updated if needed

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No sensitive data committed
```

## Branch Protection Rules

### Main Branch
- Require PR reviews (1 reviewer minimum)
- Require status checks to pass
- Require branches to be up to date
- Restrict pushes to main
- Require signed commits

### Develop Branch
- Require PR reviews (1 reviewer minimum)
- Require status checks to pass
- Allow force pushes for maintainers only

## Environment Mapping

| Branch | Environment | Auto-Deploy | Purpose |
|--------|-------------|-------------|---------|
| `main` | Production | ✅ | Live trading platform |
| `develop` | Staging | ✅ | Testing and integration |
| `feature/*` | Development | ❌ | Feature development |
| `release/*` | Pre-production | ✅ | Release testing |

## Git Commands Reference

### Common Operations

```bash
# Setup
git clone https://github.com/username/trading-platform.git
cd trading-platform
git checkout develop

# Feature development
git checkout -b feature/my-feature
git add .
git commit -m "feat: add new feature"
git push origin feature/my-feature

# Update from remote
git fetch origin
git rebase origin/develop

# Clean up merged branches
git branch -d feature/completed-feature
git push origin --delete feature/completed-feature
```

### Emergency Procedures

#### Rollback Production
```bash
# Identify last good commit
git log --oneline main

# Create hotfix branch
git checkout -b hotfix/rollback-to-<commit-hash> <commit-hash>

# Create PR and merge to main immediately
```

#### Force Update Develop
```bash
# Only for critical fixes
git checkout develop
git reset --hard origin/main
git push --force origin develop
```

## Integration with CI/CD

### Automated Checks
- **Code Quality**: ESLint, Python linting (ruff)
- **Security**: Security scanning, dependency checks
- **Testing**: Unit tests, integration tests, end-to-end tests
- **Build**: Docker image builds
- **Deploy**: Automatic deployment on merge

### Status Checks Required
- ✅ Tests pass
- ✅ Build successful
- ✅ Security scan clean
- ✅ Code coverage > 80%
- ✅ No vulnerabilities in dependencies

## Versioning Strategy

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** (v2.0.0): Breaking changes
- **MINOR** (v1.1.0): New features, backwards compatible
- **PATCH** (v1.0.1): Bug fixes, backwards compatible

### Release Tags
```bash
# Create and push release tag
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

## Best Practices

### Do's ✅
- Keep commits atomic and focused
- Write descriptive commit messages
- Rebase feature branches before merging
- Delete merged branches promptly
- Use meaningful branch names
- Test before committing
- Review your own PRs first

### Don'ts ❌
- Don't commit secrets or credentials
- Don't force push to shared branches
- Don't merge without review
- Don't commit large binary files
- Don't use generic commit messages
- Don't work directly on main/develop
- Don't ignore CI/CD failures

## Troubleshooting

### Common Issues

#### Merge Conflicts
```bash
# Pull latest changes
git fetch origin
git rebase origin/develop

# Resolve conflicts manually
# After resolving:
git add .
git rebase --continue
```

#### Accidental Commit to Wrong Branch
```bash
# Move commit to correct branch
git log --oneline  # Find commit hash
git checkout correct-branch
git cherry-pick <commit-hash>
git checkout wrong-branch
git reset HEAD~1 --hard
```

#### Recovery
```bash
# Recover lost commits
git reflog
git checkout <commit-hash>
git checkout -b recovery-branch
```

## Team Collaboration

### Code Review Process
1. Create feature branch
2. Implement changes with tests
3. Create pull request with description
4. Address review feedback
5. Merge after approval

### Communication
- Use PR comments for code discussions
- Tag relevant team members for reviews
- Update project board/issues when completing work
- Document architectural decisions in PRs

## Monitoring and Maintenance

### Repository Health
- Regular dependency updates
- Clean up stale branches monthly
- Monitor repository size
- Review access permissions quarterly

### Automation
- Automated dependency updates via Dependabot
- Automated security scanning
- Automated testing on all PRs
- Automated deployment pipelines

---

## Quick Reference Card

```bash
# Start new feature
git checkout develop && git pull && git checkout -b feature/name

# Commit with conventional format
git commit -m "feat(scope): description"

# Update feature branch
git fetch origin && git rebase origin/develop

# Create PR (use GitHub CLI)
gh pr create --title "feat: description" --body "Details"

# Merge and cleanup
gh pr merge --squash && git branch -d feature/name
```

This workflow ensures code quality, enables collaboration, and maintains a clean project history while supporting the fast-paced development needs of a trading platform.