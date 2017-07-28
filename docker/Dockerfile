FROM ubuntu:xenial
ENV PYTHONUNBUFFERED 1
RUN apt-get update
RUN apt-get install python3-pip xvfb git software-properties-common -y
RUN apt-get install software-properties-common -y &&\
    add-apt-repository ppa:thopiekar/pyside-git -y &&\
    apt-get remove software-properties-common -y
RUN apt-get update
RUN apt-get install python3-pyside2 -y
RUN apt-get clean
RUN pip3 install xvfbwrapper
RUN pip3 install ghost.py --pre
