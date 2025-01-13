FROM fedora:latest
RUN dnf -y install python36 python3-pytest python3-pip git libselinux-utils tuned sysstat hatch python38 python39 python310 python311 python312
RUN git config --global http.sslVerify false

