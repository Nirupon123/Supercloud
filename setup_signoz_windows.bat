@echo off

echo Cloning SigNoz repository...
git clone -b main https://github.com/SigNoz/signoz.git

echo Entering deploy folder...
cd signoz\deploy

echo Entering docker folder...
cd docker

echo Starting docker compose...
docker compose up

echo Setup complete!
pause