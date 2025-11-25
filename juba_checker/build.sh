#!/bin/bash

echo "Building Juba Checker Executable..."
echo ""

pyinstaller --onefile --name juba_checker_cli juba_checker.py
pyinstaller juba_checker.spec

echo ""
echo "Build complete! Executables are in the dist/ folder."
echo "- juba_checker_cli (CLI only)"
echo "- juba_checker (Web interface)"
