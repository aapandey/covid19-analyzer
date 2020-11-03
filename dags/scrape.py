from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import urllib.request, json
import pandas as pd
import airflow
import logging, os
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook
import sqlalchemy


provisional_death_filepath = Variable.get(
    "provisional_death_path",
    default_var="/usr/local/airflow/workspace/provisional-death/file.csv",
)

with open("/usr/local/airflow/dags/files/state.json") as json_file:
    state_abbr = json.load(json_file)


# This method writes to a local file the request result from the input_url and search_key
def download_provisional_death_json_file(**kwargs):
    input_url = kwargs["input_url"]
    search_key = kwargs["search_key"]
    filepath = kwargs["filepath"]
    os.remove(filepath) if os.path.exists(filepath) else None
    logging.info(f"source: {input_url} dn search {search_key}")
    with urllib.request.urlopen(input_url) as url:
        data = json.loads(url.read().decode())
    for obj in data["dataset"]:
        if obj["title"] == search_key:
            for d in obj["distribution"]:
                if d["format"] == "csv":
                    logging.info(f"Downloading from {d['downloadURL']} tp {filepath}")
                    urllib.request.urlretrieve(d["downloadURL"], filepath)
                    return


# Given a file, this method transforms the data and loads it into the database
def read_and_load(**kwargs):
    filepath = kwargs["filepath"]
    cols = kwargs["cols"]
    rename_dict = kwargs["rename_dict"]
    df = pd.read_csv(filepath)
    logging.info(f"{df.head()}")

    conn = BaseHook.get_connection('postgres_dev')
    logging.info(f"postgres conn string is {conn.get_uri()}")
    engine = sqlalchemy.create_engine(conn.get_uri())

    for state in state_abbr.keys():
        subset_df = df.loc[df['state'] == state][cols]
        subset_df = subset_df.rename(columns=rename_dict)
        if not subset_df.empty:
            subset_df.to_sql(
                state_abbr[state].lower(),
                con=engine,
                index=False,
                schema="covid",
                index_label=None,
                dtype={
                    "date": sqlalchemy.types.Date,
                    "total_cases": sqlalchemy.types.BigInteger,
                    "new_cases": sqlalchemy.types.BigInteger,
                    "total_deaths": sqlalchemy.types.BigInteger,
                    "new_deaths": sqlalchemy.types.BigInteger,
                },
                if_exists='replace'
            )


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": airflow.utils.dates.days_ago(2),
    "retries": 1,
}

# Set Schedule: Run pipeline once a day.
# Use cron to define exact time (UTC). Eg. 8:15 AM would be '15 08 * * *'
schedule_interval = "30 09 * * *"


dag = DAG(
    dag_id="scraping_and_loading_data",
    default_args=default_args,
    schedule_interval=schedule_interval,
)

# Task 1: scraping data
summary_scraping = PythonOperator(
    task_id="summary_scraping_data",
    python_callable=download_provisional_death_json_file,
    op_kwargs={
        "input_url": "https://healthdata.gov/data.json?page=0",
        "search_key": "United States COVID-19 Cases and Deaths by State over Time",
        "filepath": provisional_death_filepath,
    },
    provide_context=True,
    dag=dag,
)

# task2 transforming and loading
read_and_load = PythonOperator(
    task_id="read_and_load",
    python_callable=read_and_load,
    op_kwargs={
        "filepath": provisional_death_filepath,
        "cols": ["submission_date", "tot_cases", "new_case", "tot_death", "new_death"],
        "rename_dict": {
            "submission_date": "date",
            "tot_cases": "total_cases",
            "new_case": "new_cases",
            "tot_death": "total_deaths",
            "new_death": "new_deaths"
        },
    },
    provide_context=True,
    dag=dag,
)

summary_scraping >> read_and_load
