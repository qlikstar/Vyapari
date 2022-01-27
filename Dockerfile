FROM qlikstar/python-39-ta-lib:1.1

RUN git clone https://github.com/qlikstar/fmp_python.git
RUN pip install -e fmp_python

WORKDIR /home/app

COPY . /home/app
ADD requirements.txt .
RUN pip install --upgrade pip
RUN pip install --trusted-host pypi.python.org -r requirements.txt

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]