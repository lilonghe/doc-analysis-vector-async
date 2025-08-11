# 简化的PDF解析服务 - 先使用PyPDF2实现基础功能
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制API服务文件
COPY api.py /app/api.py
COPY requirements.txt /app/requirements.txt

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p /app/uploads /app/temp /app/output

# 暴露端口
EXPOSE 8888

# 启动API服务
CMD ["python", "api.py"]