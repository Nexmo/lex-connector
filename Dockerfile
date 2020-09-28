FROM python:3.8.3
WORKDIR /usr/src/lex-connector
COPY .env.example .env
COPY . .
RUN pip install --upgrade -r requirements.txt
CMD ["python", "server.py"]
EXPOSE 5000