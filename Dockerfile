ARG UBUNTU_VERSION=22.04
FROM ubuntu:${UBUNTU_VERSION}

ARG PROJECT_NAME=query
ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y \
        git \
        curl \
        python3 \
    && rm -rf /var/lib/apt/lists/*

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER ${USERNAME}
WORKDIR /workspaces/${PROJECT_NAME}
ENV VIRTUAL_ENV /workspaces/${PROJECT_NAME}/.venv
ENV PYTHONPATH=/workspaces/${PROJECT_NAME}

RUN cat >> /home/${USERNAME}/.bashrc <<'EOF'

# bash completion
source /usr/share/bash-completion/completions/git 
source /usr/lib/git-core/git-sh-prompt

export GIT_PS1_SHOWDIRTYSTATE=1
export GIT_PS1_SHOWUNTRACKEDFILES=1

ORIGINAL_PS1="$PS1"
GIT_COLOR="\[\033[38;5;216m\]"
RESET="\[\033[00m\]"

PS1="${ORIGINAL_PS1%\\$ }"'$(__git_ps1 " '"$GIT_COLOR"'(%s)'"$RESET"'")'"\\$ "
EOF

# Use bash for the shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
