FROM python:3.12-alpine
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x entrypoint.sh
EXPOSE 5000
CMD ["./entrypoint.sh"]
