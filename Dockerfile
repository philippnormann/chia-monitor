FROM fsfe/pipenv:python-3.8

WORKDIR /chia-monitor
COPY Pipfile Pipfile.lock alembic.ini ./
RUN pipenv install alembic
RUN pipenv install
COPY . .
RUN pipenv run alembic upgrade head

VOLUME [ "/chia-monitor/config.json", "/root/.chia" ]
EXPOSE 8000

ENTRYPOINT pipenv run python -m monitor
