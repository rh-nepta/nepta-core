FROM fedora
RUN dnf -y install python36 python3-pytest python3-pip git pipenv libselinux-utils tuned sysstat hatch tox python37 python38 python39 python310 python311 python312
RUN git config --global http.sslVerify false

