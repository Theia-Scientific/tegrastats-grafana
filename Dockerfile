FROM ubuntu:20.04

## Build Arguments

ARG DEBIAN_FRONTEND=noninteractive

## Package Installer for Python (PIP)
ARG PIP_ROOT_USER_ACTION=ignore \
    PIP_DEFAULT_TIMEOUT=100

## Python
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

## Timezone
ENV TZ=UTC

## Install Python, L4T, and CUDA packages
RUN echo "deb [trusted=yes] https://repo.download.nvidia.com/jetson/common r35.1 main" > /etc/apt/sources.list.d/nvidia-l4t-apt-source.list && \
    echo "deb [trusted=yes] https://repo.download.nvidia.com/jetson/t234 r35.1 main" >> /etc/apt/sources.list.d/nvidia-l4t-apt-source.list && \
    apt-get update -y && \
    apt-get install -y tzdata python3.8 python3-pip && \
    mkdir -p /opt/nvidia/l4t-packages/ && \
    touch /opt/nvidia/l4t-packages/.nv-l4t-disable-boot-fw-update-in-preinstall && \
    apt-get install -y nvidia-l4t-tools && \
    rm -rf /var/lib/apt/lists/* &&  \
    apt-get clean

## Working directory
WORKDIR /app

## Upgrade PIP and install dependencies
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt && \
    python3 -m pip install --no-cache-dir -U -v jetson-stats

## Copy Python scripts
COPY serve.py ./serve.py

CMD ["python3", "/app/serve.py"]
