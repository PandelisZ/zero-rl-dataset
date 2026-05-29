# syntax=docker/dockerfile:1
#
# Prime training/eval sandbox image: zerolang toolchain + Roder harness.
# Build (amd64 required for the Roder binary):
#   docker build --platform=linux/amd64 -t zero-roder-sandbox envs/zero_verifiers_env/sandbox
# Use as the Prime sandbox image (CliAgentEnv/SandboxSpec `docker_image`), or
# reference it from prime/train.roder.toml.
FROM --platform=linux/amd64 python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/root

COPY install.sh /opt/install.sh
COPY score.sh /opt/score.sh
RUN chmod +x /opt/install.sh /opt/score.sh && bash /opt/install.sh

# Put both toolchains on PATH for every later shell / agent invocation.
ENV PATH="/root/.zero/bin:/root/.roder/bin:${PATH}"

WORKDIR /app
CMD ["bash"]
