FROM python:2.7

WORKDIR /app
ENV PYTHONPATH /app

# Install mysql-connector-python
RUN git clone --branch 2.1.3 https://github.com/mysql/mysql-connector-python.git
RUN cd mysql-connector-python; python ./setup.py build; python ./setup.py install

# Install pip requirements
ADD requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app/

CMD ["python", "/app/app.py"]

EXPOSE 5000
