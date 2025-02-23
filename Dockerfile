# 使用Python 3.11作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置Python环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建配置文件
RUN cp app/config.example.py app/config.py

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["python", "run.py"]

# 新增Dockerfile指令
RUN mkdir -p /app/data && \
    chmod 700 /app/data && \
    chown nobody:nogroup /app/data
USER nobody