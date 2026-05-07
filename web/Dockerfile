# ==================== Vue 前端构建 ====================
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN npm install -g pnpm && pnpm install

COPY . .
RUN pnpm build

# ==================== Nginx 运行 ====================
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY deployments/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
