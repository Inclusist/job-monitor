You have a Claude Code process still running. Here's the fix:

  Step 1: Exit Claude Code Completely

  First, close this Claude session completely (not just this conversation). Type exit or press Ctrl+D to fully quit.

  Step 2: Remove the Old Package

  After exiting, run these commands:

  # Remove the old package directory
  rm -rf /Users/prabhu.ramachandran/.npm-global/lib/node_modules/@anthropic-ai/claude-code

  # Clear npm cache (optional but helps)
  npm cache clean --force

  # Reinstall Claude Code
  npm i -g @anthropic-ai/claude-code

  Alternative: Force Reinstall in One Command

  npm i -g @anthropic-ai/claude-code --force

  If That Still Fails

  Try this nuclear option:

  # Remove the entire @anthropic-ai directory
  rm -rf /Users/prabhu.ramachandran/.npm-global/lib/node_modules/@anthropic-ai

  # Clean cache
  npm cache clean --force

  # Reinstall
  npm i -g @anthropic-ai/claude-code

  After Installation

  Verify the update worked:

  claude --version

  The issue is that npm can't update while Claude Code is running and has files open. Once you exit completely and remove the directory, the installation should succeed.