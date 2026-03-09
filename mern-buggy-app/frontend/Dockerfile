# Frontend Dockerfile - Multi-stage build

# Stage 1: Build the React application
FROM node:18-alpine as build-stage

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
# Ensure production build
RUN npm install


# Expose port 80
EXPOSE 3000

CMD ["npm", "start"]
