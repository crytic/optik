FROM trailofbits/echidna:latest

RUN apt-get update && apt-get install -y python3.8-dev
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.8 1 && \
    update-alternatives  --set python /usr/bin/python3.8

RUN python -m pip install --upgrade pip

RUN mkdir /optik
COPY . /optik

WORKDIR /optik

RUN python -m pip install .

RUN mkdir /workdir

WORKDIR /workdir
