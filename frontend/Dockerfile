# Dockerfile for Next.js frontend
FROM node:20-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-alpine as runner
WORKDIR /app
ENV NODE_ENV=production
# --- ADD THESE TWO LINES TO FIX THE TIMEOUT ---
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
# ----------------------------------------------
COPY --from=builder /app .
EXPOSE 3000
CMD ["npm", "start"]
