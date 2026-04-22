# 基础镜像选择官方Python3最新稳定版
FROM python:3.11-slim

# 维护者信息
LABEL maintainer="zxdy@example.com"

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    # 时区设置
    TZ=Asia/Shanghai \
    # Python 不生成 .pyc 文件
    PYTHONDONTWRITEBYTECODE=1 \
    # Python 缓冲输出
    PYTHONUNBUFFERED=1 \
    # pip 国内源
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 更换 Debian 源为阿里云
RUN echo "deb http://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装常用工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基础工具
    git \
    openssh-client \
    openssh-server \
    curl \
    wget \
    vim \
    # 网络工具
    net-tools \
    iputils-ping \
    telnet \
    # 系统工具
    procps \
    htop \
    tree \
    # 编译依赖（可选，如需安装需要编译的Python包）
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    # 清理缓存减小镜像体积
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 配置 vim 基础环境
RUN echo "set nu\nset tabstop=4\nset shiftwidth=4\nset expandtab\nset autoindent" > /root/.vimrc

# 配置 SSH 客户端（可选，解决首次连接主机时的确认提示）
RUN mkdir -p /root/.ssh && \
    echo "StrictHostKeyChecking no" > /root/.ssh/config && \
    chmod 600 /root/.ssh/config



# 配置SSH服务
RUN mkdir -p /var/run/sshd \
    # 设置root密码
    && echo "root:123456" | chpasswd \
    # 修改SSH配置，允许root登录和密码认证
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    # 生成SSH密钥
    && ssh-keygen -A \
    # 设置目录权限
    && chmod 755 /var/run/sshd


# 暴露SSH端口
EXPOSE 22
EXPOSE 5001

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装（如需）
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# 拷贝当前项目到/app目录下（.dockerignore中文件除外）
COPY . /app
RUN pip install --no-cache-dir -r /app/requirements.txt

# 创建启动脚本
RUN echo '#!/bin/bash\n\
# 启动SSH服务\n\
/usr/sbin/sshd -D &\n\
python3 /app/app.py \n\' > /start.sh && \
    chmod +x /start.sh

# 容器启动执行启动脚本
CMD ["/start.sh"]