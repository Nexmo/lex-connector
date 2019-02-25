FROM python:2.7.15
WORKDIR /usr/src/lex-connector
COPY .env.example .env
COPY . .
RUN pip install --upgrade -r requirements.txt
CMD ["python", "server.py"]
EXPOSE 5000