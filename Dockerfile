# Image de l'API pour Render. Elle sert aussi la page web, ce qui permet de tout lancer en local avec une seule commande.
FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requirements-app.txt .
RUN pip install --no-cache-dir --user -r requirements-app.txt

COPY --chown=user src ./src
COPY --chown=user api ./api
COPY --chown=user app/provisoire.py ./app/provisoire.py
COPY --chown=user web ./web
COPY --chown=user data/original/Train.csv ./data/original/Train.csv
COPY --chown=user models ./models

# Render fournit le port dans la variable PORT.
ENV PORT=10000
EXPOSE 10000
CMD uvicorn api.main:app --host 0.0.0.0 --port $PORT
