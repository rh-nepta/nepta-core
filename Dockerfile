FROM fedora
RUN dnf -y install python36 python3-pytest git pipenv libselinux-utils tuned python38 python39 python37 tox
RUN pip3 install pip pipenv -U
RUN git config --global http.sslVerify false

