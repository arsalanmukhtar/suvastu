FROM node:22-alpine AS base
WORKDIR /app
COPY package*.json ./

FROM base AS dev
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM base AS build
RUN npm install
COPY . .
ARG VITE_API_URL=/api
ARG VITE_TILER_URL=/tiles
ARG VITE_MAPBOX_TOKEN
ARG VITE_MAPBOX_STYLE=mapbox://styles/mapbox/satellite-streets-v12
ENV VITE_API_URL=$VITE_API_URL VITE_TILER_URL=$VITE_TILER_URL \
    VITE_MAPBOX_TOKEN=$VITE_MAPBOX_TOKEN VITE_MAPBOX_STYLE=$VITE_MAPBOX_STYLE
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
