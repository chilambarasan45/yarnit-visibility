# Frontend Dockerfile — Yarnit AI Visibility Platform

FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Bake the API key in at build time so the frontend can talk to the
# backend without any manual setup on the CEO's machine.
ARG REACT_APP_API_KEY
ENV REACT_APP_API_KEY=$REACT_APP_API_KEY

RUN npm run build

# Serve the built static files with a tiny, fast static server
FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/build ./build

EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
