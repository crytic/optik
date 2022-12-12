FROM trailofbits/echidna:latest

COPY . /optik
RUN pip3 install --no-cache-dir /optik

WORKDIR /workdir
