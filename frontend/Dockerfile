# ===========================================
# AI Audiobook Workshop - Frontend Dockerfile (Dev Mode)
# ===========================================

FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install || true

# Copy source (placeholder for now)
COPY frontend/ ./

# Expose port
EXPOSE 3000

# Start dev server
CMD ["npm", "run", "dev"]
