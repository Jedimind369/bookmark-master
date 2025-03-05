FROM node:20-alpine

WORKDIR /app

# Install dependencies
RUN apk add --no-cache python3 make g++ git

# Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# TypeScript zu JavaScript konvertieren
RUN npm run build

# Fix any line ending issues
RUN sed -i '$ s/%$//' /app/src/server/index.ts

# Rebuild bcrypt for Alpine
WORKDIR /app/src/server
RUN npm uninstall bcrypt
RUN npm install bcrypt --build-from-source

# Copy conversion scripts
COPY convert.cjs /app/convert.cjs
COPY auth-convert.cjs /app/auth-convert.cjs
COPY index-convert.cjs /app/index-convert.cjs
COPY auth-routes-convert.cjs /app/auth-routes-convert.cjs
COPY auth-utils-convert.cjs /app/auth-utils-convert.cjs
COPY auth-middleware-convert.cjs /app/auth-middleware-convert.cjs

# Make scripts executable
RUN chmod +x /app/*.cjs

# Create dist directory
RUN mkdir -p /app/src/server/dist/routes

# Run conversion scripts
RUN node /app/index-convert.cjs
RUN node /app/auth-utils-convert.cjs
RUN node /app/auth-middleware-convert.cjs
RUN node /app/auth-convert.cjs
RUN node /app/auth-routes-convert.cjs

# Debug: List files in dist directory
RUN ls -la /app/src/server/dist/

# Debug: Check the content of the index.js file
RUN head -n 50 /app/src/server/dist/index.js

# Generate Prisma client
WORKDIR /app/src/server
RUN npx prisma generate

# Set environment variables
ENV NODE_ENV=production
ENV PORT=8000

# Expose port
EXPOSE 8000

# Start the application
CMD ["node", "dist/index.js"] 