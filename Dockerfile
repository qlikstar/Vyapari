FROM qlikstar/python-39-ta-lib:1.0

WORKDIR /home/app

COPY . /home/app
ADD requirements.txt .
RUN pip install --upgrade pip
RUN pip install --trusted-host pypi.python.org -r requirements.txt

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]