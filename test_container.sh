#!/bin/bash

# Exit on any error
set -e

echo "Building test container..."
docker build -t tennisbooking:testing -f build/Dockerfile .

echo "Running tests in container..."
docker run --rm tennisbooking:testing python -m pytest src/ -v

echo "Tests completed successfully!" 