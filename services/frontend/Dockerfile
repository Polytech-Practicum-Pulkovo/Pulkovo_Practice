FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
# Реестр npm из этого окружения периодически обрывает соединение на больших
# установках — повторяем попытку вместо однократного npm ci.
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && for i in 1 2 3; do npm ci && break || sleep 5; done \
    && test -d node_modules/.bin

COPY . .

ARG VITE_PERSONAL_DATA_URL=http://localhost:8001
ARG VITE_PROGRESS_LOADER_URL=http://localhost:8002
ARG VITE_NOTIFICATIONS_URL=http://localhost:8003
ARG VITE_AI_GENERATION_URL=http://localhost:8004
ARG VITE_COURSE_PROGRESS_URL=http://localhost:8005
ARG VITE_COURSE_MANAGEMENT_URL=http://localhost:8006

ENV VITE_PERSONAL_DATA_URL=$VITE_PERSONAL_DATA_URL \
    VITE_PROGRESS_LOADER_URL=$VITE_PROGRESS_LOADER_URL \
    VITE_NOTIFICATIONS_URL=$VITE_NOTIFICATIONS_URL \
    VITE_AI_GENERATION_URL=$VITE_AI_GENERATION_URL \
    VITE_COURSE_PROGRESS_URL=$VITE_COURSE_PROGRESS_URL \
    VITE_COURSE_MANAGEMENT_URL=$VITE_COURSE_MANAGEMENT_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
