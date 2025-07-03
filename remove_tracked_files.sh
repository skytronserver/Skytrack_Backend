#!/bin/bash

# This script will remove files from Git tracking while keeping them in your local workspace
# This ensures .gitignore rules are properly applied to already tracked files

echo "Removing tracked files listed in .gitignore from Git repository..."

# First, we'll remove all files from the Git cache
git rm --cached -r .

# Then we'll add back all files
git add .

# This effectively applies the .gitignore rules by removing the tracked files
# that match the .gitignore patterns while keeping the local files intact

echo "Files have been removed from Git tracking but kept in your local workspace."
echo "You'll need to commit these changes with:"
echo "git commit -m \"Remove ignored files from tracking\""
