FROM apache/airflow:3.3.2-python3.12

USER root

# Crear entorno virtual aislado para dbt en /opt/dbt-venv
RUN python -m venv /opt/dbt-venv \
    && chown -R airflow:root /opt/dbt-venv

USER airflow

# Instalar dependencias de dbt dentro del entorno virtual aislado
COPY --chown=airflow:root requirements-dbt.txt /opt/airflow/requirements-dbt.txt
RUN /opt/dbt-venv/bin/pip install --no-cache-dir -r /opt/airflow/requirements-dbt.txt

# Instalar dependencias de scripts de ingesta para Airflow
COPY --chown=airflow:root requirements.txt /opt/airflow/requirements.txt
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt

# Exponer el binario de dbt en el PATH (al final para no opacar el python de Airflow)
ENV PATH="${PATH}:/opt/dbt-venv/bin"
