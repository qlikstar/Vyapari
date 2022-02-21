# Build Base image file
FROM python:3.9

# set env variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# set timezone to PST
ENV TZ America/Los_Angeles

# install git
RUN apt-get -y update
RUN apt-get -y install git

# upgrade pip
RUN pip install --upgrade pip

# TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
  tar -xvzf ta-lib-0.4.0-src.tar.gz && \
  cd ta-lib/ && \
  ./configure --prefix=/usr && \
  make && \
  make install

RUN rm -R ta-lib ta-lib-0.4.0-src.tar.gz

CMD echo "Python 3.9 with TA-Lib installed"