#!/usr/bin/env node

/**
 * File watcher script for automatic frontend rebuilds
 * Monitors JSX/TSX file changes and triggers npm build
 */

const { spawn, exec } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('🚀 Starting frontend file watcher...');
console.log('📁 Watching for changes in JSX/TSX files...');

let buildInProgress = false;
let buildTimeout = null;

// Function to trigger build
function triggerBuild() {
  if (buildInProgress) {
    console.log('⏳ Build already in progress, skipping...');
    return;
  }

  console.log('🔨 JSX file changed, triggering build...');
  buildInProgress = true;

  const buildProcess = spawn('npm', ['run', 'build'], {
    stdio: 'inherit',
    shell: true
  });

  buildProcess.on('close', (code) => {
    buildInProgress = false;
    if (code === 0) {
      console.log('✅ Build completed successfully');
    } else {
      console.log('❌ Build failed with code:', code);
    }
  });

  buildProcess.on('error', (error) => {
    buildInProgress = false;
    console.error('❌ Build error:', error);
  });
}

// Function to watch directory recursively
function watchDirectory(dir) {
  console.log(`👀 Watching directory: ${dir}`);

  // Watch the current directory
  const watcher = fs.watch(dir, { recursive: true }, (eventType, filename) => {
    if (!filename) return;

    const filePath = path.join(dir, filename);
    const ext = path.extname(filename);

    // Check if it's a JSX/TSX file
    if ((ext === '.jsx' || ext === '.tsx' || ext === '.js' || ext === '.ts') &&
        !filename.includes('node_modules') &&
        !filename.includes('.next') &&
        !filename.includes('build')) {

      console.log(`📝 File ${eventType}: ${filename}`);

      // Clear existing timeout
      if (buildTimeout) {
        clearTimeout(buildTimeout);
      }

      // Set new timeout to avoid too frequent builds
      buildTimeout = setTimeout(() => {
        triggerBuild();
      }, 1000); // Wait 1 second after last change
    }
  });

  return watcher;
}

// Function to check if file exists and is a directory
function isDirectory(filePath) {
  try {
    return fs.statSync(filePath).isDirectory();
  } catch (error) {
    return false;
  }
}

// Start watching the src directory
const srcDir = path.join(__dirname, 'src');
if (isDirectory(srcDir)) {
  watchDirectory(srcDir);
} else {
  console.error('❌ src directory not found');
  process.exit(1);
}

// Handle process termination
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down file watcher...');
  if (buildTimeout) {
    clearTimeout(buildTimeout);
  }
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Received SIGTERM, shutting down...');
  if (buildTimeout) {
    clearTimeout(buildTimeout);
  }
  process.exit(0);
});

console.log('✅ File watcher started successfully');
console.log('💡 The watcher will automatically rebuild when JSX/TSX files change');
console.log('🔄 Press Ctrl+C to stop the watcher');