#!/bin/bash

echo "Cloning SigNoz repository..."
git clone -b main https://github.com/SigNoz/signoz.git

echo "Moving into deploy directory..."
cd signoz/deploy || exit

echo "Moving into docker directory..."
cd docker || exit

echo "Starting docker compose..."
docker compose up

echo "Setup complete!"