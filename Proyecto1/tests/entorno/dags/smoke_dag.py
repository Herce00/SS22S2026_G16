from datetime import datetime
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

with DAG(
    dag_id="smoke_test_task_execution",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
) as dag:
    SQLExecuteQueryOperator(
        task_id="test_select_1_dw",
        conn_id="sgfood_dw",
        sql="SELECT 1;",
    )
