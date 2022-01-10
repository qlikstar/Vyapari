FROM python:3.9

RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
  tar -xvzf ta-lib-0.4.0-src.tar.gz && \
  cd ta-lib/ && \
  ./configure --prefix=/usr && \
  make && \
  make install
#RUN git clone https://github.com/mrjbq7/ta-lib.git /ta-lib-py && cd ta-lib-py && python setup.py install

WORKDIR /home/app

COPY . /home/app
ADD requirements.txt .
RUN pip install --trusted-host pypi.python.org -r requirements.txt


# FastAPIを8000ポートで待機
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]