# Node.js Development in Python Execution Platform

## Overview

The Python Execution Platform now supports Node.js development alongside Python. However, Node.js projects can create very large `node_modules` directories that may impact performance.

## Best Practices

### 🚀 Quick Start

1. **Create your project files** (package.json, etc.)
2. **Use optimized install commands** instead of regular `npm install`
3. **Monitor directory sizes** to avoid performance issues

### 🛡️ Optimized npm Commands

The container includes several optimized npm commands:

#### `npm-safe` - Recommended for most projects
```bash
npm-safe
# Installs with optimizations: --no-audit --no-fund --prefer-offline
```

#### `npm-light` - For production builds
```bash
npm-light
# Installs only production dependencies: --production --no-optional --no-audit --no-fund
```

#### `npm-clean` - Clean up before fresh install
```bash
npm-clean
# Removes node_modules, package-lock.json, and clears npm cache
```

### 📊 Monitoring

After installing packages, the container will show:
- `node_modules` directory size
- Performance tips

### 🚫 What to Avoid

**Don't use regular `npm install`** for large projects:
```bash
# ❌ This can create 500MB+ directories
npm install

# ✅ Use this instead
npm-safe
```

## Example Workflow

### Creating a Vite App

```bash
# 1. Create the project
npm create vite@latest my-app
cd my-app

# 2. Install dependencies with optimization
npm-safe

# 3. Check the size
ls -lah node_modules/

# 4. If too large, use production-only
npm-clean
npm-light
```

### Working with Existing Projects

```bash
# 1. Clone or create your project files
# 2. Clean install with optimizations
npm-clean
npm-safe

# 3. For development dependencies
npm-dev
```

## File System Exclusions

The platform automatically excludes these directories from file listings to improve performance:

- `node_modules/` - npm packages
- `.git/` - Git repositories
- `venv/` - Python virtual environments
- `__pycache__/` - Python cache
- `dist/`, `build/` - Build outputs
- `.next/`, `.nuxt/` - Framework caches
- `coverage/` - Test coverage

## Troubleshooting

### Container Running Slowly
- Check `node_modules` size: `du -sh node_modules`
- Use `npm-clean` and `npm-light` for smaller footprint
- Consider using `yarn` with `--production` flag

### File Tree Not Loading
- Large `node_modules` can cause timeouts
- The platform automatically excludes them from listings
- Use the terminal to navigate large directories

### Container Crashes
- Very large installations (1GB+) can exceed container limits
- Use `npm-light` for essential packages only
- Consider using CDN links for frontend libraries instead of npm

## Tips

1. **Start small** - Install only essential packages initially
2. **Use CDNs** - For frontend libraries, consider CDN links over npm packages
3. **Production builds** - Use `npm-light` for final builds
4. **Monitor size** - Keep `node_modules` under 200MB when possible
5. **Clean regularly** - Use `npm-clean` between different projects

## Available Tools

- **Node.js**: Latest LTS version
- **npm**: Latest version with optimized configuration
- **yarn**: Available as alternative package manager
- **pnpm**: Available for even smaller installs