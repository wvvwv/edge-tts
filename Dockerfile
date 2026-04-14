# 使用轻量级的 Python 基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装必要的系统依赖（如果 edge-tts 需要的话，通常不需要额外依赖，但保持基础镜像干净）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY main.py .

# 暴露端口（Render 会通过环境变量 $PORT 覆盖，但这里显式声明以作参考）
EXPOSE 8000

# 启动命令
# 注意：使用 0.0.0.0 以便在容器外访问
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
