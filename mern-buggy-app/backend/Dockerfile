# Backend Dockerfile

FROM node:18-alpine

# Create app directory
WORKDIR /usr/src/app

# Install app dependencies
COPY package*.json ./

# Install dependencies (production only for optimized size)
RUN npm install --omit=dev

# Bundle app source
COPY . .

# The app listens on port 3001
EXPOSE 3001

# Run with OpenTelemetry required
CMD [ "node", "--require", "./otel.js", "server.js" ]
