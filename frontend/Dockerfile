# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files first
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy source code (this won't overwrite node_modules if we're careful)
COPY frontend/src ./src
COPY frontend/index.html ./
COPY frontend/vite.config.js ./

# Build the app with API base URL from build arg or default
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
