# 使用国内镜像
FROM node:18-alpine AS builder

# 设置npm镜像源
RUN npm config set registry https://registry.npmmirror.com/

WORKDIR /app

# 安装pnpm并设置镜像
RUN npm install -g pnpm && \
    pnpm config set registry https://registry.npmmirror.com/

# 复制包文件（利用Docker缓存）
COPY package.json pnpm-lock.yaml ./

# 安装依赖（使用缓存和挂载）
RUN --mount=type=cache,target=/root/.pnpm-store \
    pnpm install --frozen-lockfile

# 复制配置文件（利用缓存）
COPY tailwind.config.js vite.config.ts tsconfig.json* postcss.config.js ./

# 复制源代码
COPY src/ ./src/
COPY index.html ./
COPY public/ ./public/ 2>/dev/null || true

# 构建应用
RUN pnpm build

# 生产环境使用nginx（使用国内镜像）
FROM nginx:alpine AS production

# 使用国内镜像源
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories

# 复制构建结果
COPY --from=builder /app/dist /usr/share/nginx/html
COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf

# 修改nginx配置以支持非root用户
RUN sed -i '/user  nginx;/d' /etc/nginx/nginx.conf && \
    sed -i 's/listen  *80;/listen 8080;/' /etc/nginx/conf.d/default.conf && \
    sed -i 's/listen \[::\]:80;/listen [::]:8080;/' /etc/nginx/conf.d/default.conf && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /etc/nginx/conf.d

USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]