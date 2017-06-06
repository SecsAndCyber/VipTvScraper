FROM consol/centos-xfce-vnc:1.0.1
MAINTAINER Matthew Molyett <matthewmolyett@gmail.com>

RUN yum -y install http://linuxdownload.adobe.com/linux/x86_64/adobe-release-x86_64-1.0-1.noarch.rpm
RUN yum install -y flash-plugin
RUN yum install -y unzip


COPY install /install
RUN tar -xzf /install/geckodriver-v0.11.1-linux32.tar.gz -C /usr/local/sbin
RUN unzip -d /browsermob-proxy /install/browsermob-proxy-2.1.3-bin.zip

RUN python /install/get-pip.py
RUN python -m pip install -U selenium==2.53.0 browsermob-proxy

COPY scripts /scripts
RUN chmod +x /scripts/*