FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build (for production) or run dev server
ENV NODE_ENV=development
EXPOSE 3000

CMD ["npm", "run", "dev"]
