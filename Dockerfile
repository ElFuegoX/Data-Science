# Image de l'application pour un Space Hugging Face (SDK Docker) : l'API FastAPI sert aussi la page web.
FROM python:3.12-slim

# Hugging Face lance le conteneur avec l'utilisateur 1000.
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

EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
