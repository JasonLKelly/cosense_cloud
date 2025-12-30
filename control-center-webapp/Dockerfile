FROM node:20-slim AS builder

WORKDIR /app

# Accept build-time env vars for Vite
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage - serve with a simple static server
FROM node:20-slim

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
