FROM python:3.12-slim

# Write print() output to stdout immediately, so it appears in 'azd ai agent monitor'
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . user_agent/
WORKDIR /app/user_agent

RUN if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    else \
        echo "No requirements.txt found"; \
    fi

EXPOSE 8088

CMD ["python", "main.py"]


# Developer Notes:
# docker images | grep agent  
# docker build -t cjoakim/epl .                            (on Windows)
# docker build --platform linux/amd64 -t cjoakim/epl .     (on macOS)
# docker tag cjoakim/epl:latest crcjoakimforge1022a.azurecr.io/epl:1
#
# az acr login --name crcjoakimforge1022a
# docker tag cjoakim/epl:latest crcjoakimforge1022a.azurecr.io/epl:v3
# docker push crcjoakimforge1022a.azurecr.io/epl:v3
# az acr repository list --name crcjoakimforge1022a -o table
# az acr repository show --name crcjoakimforge1022a --image epl:v3