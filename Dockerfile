FROM python:2.7.15
WORKDIR /usr/src/lex-connector
COPY . .
RUN pip install --upgrade -r requirements.txt
CMD ["python", "server.py", "--config", "lexmo.conf"]
EXPOSE 5000