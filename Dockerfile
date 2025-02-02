FROM python:3.8-slim-bullseye
# FROM cytomine/software-python3-base:v2.2.0
# RUN python -m pip install -U --force-reinstall pip
# RUN apt-get update -y && apt-get install -y git libgeos-dev libglib2.0-0
# RUN apt-get update && apt-get install --no-install-recommends --no-install-suggests -y curl
# RUN apt-get install unzip
# RUN apt-get -y install python3
# RUN apt-get -y install python3-pip

RUN python -m pip install -U --force-reinstall pip
RUN apt-get update -y && apt-get install -y git libgeos-dev libglib2.0-0

COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt
RUN pip3 install scikit-image

COPY run.py /app/run.py
RUN git clone https://github.com/cytomine/Cytomine-python-client.git && \
    cd Cytomine-python-client && \
    git checkout v2.2.0 && \
    python setup.py build && \
    python setup.py install



ENTRYPOINT ["python", "/app/run.py"]
