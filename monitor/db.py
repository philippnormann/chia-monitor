import databases
import sqlalchemy

database = databases.Database("sqlite:///history.sqlite")
metadata = sqlalchemy.MetaData()
engine = sqlalchemy.create_engine(str(database.url))


def create_all_tables() -> None:
    metadata.create_all(engine)
