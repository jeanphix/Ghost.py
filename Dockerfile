FROM ubuntu:xenial
ENV PYTHONUNBUFFERED 1
RUN apt-get update
RUN apt-get install python3-pip xvfb git software-properties-common -y
RUN add-apt-repository ppa:thopiekar/pyside-git -y
RUN apt-get update
RUN apt-get install python3-pyside2 -y
RUN apt-get clean
RUN pip3 install flask xvfbwrapper
WORKDIR /ghost
ADD . .
