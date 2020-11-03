import pandas as pd
import logging
import sqlalchemy
from matplotlib import pyplot


def generate_plot(table_name, schema_name, con_str):
    logging.info(f"postgres conn string is {con_str}")
    engine = sqlalchemy.create_engine(con_str)

    df = pd.read_sql_table(table_name, con=engine, schema=schema_name)
    logging.info(f"{df.head()}")
    df.date = pd.to_datetime(df.date)
    dg = df.groupby(pd.Grouper(key='date', freq='1M')).sum()  # groupby each 1 month
    dg.index = dg.index.strftime('%B')

    dg.plot(kind='bar', subplots=True, title=f"State of {table_name} Covid cases")
    pyplot.show()


if __name__ == "__main__":
    generate_plot("illinois", "covid", "postgresql://admin:abcxyz@localhost:5433/postgres")
