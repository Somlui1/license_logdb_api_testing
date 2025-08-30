from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Numeric, create_engine, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
schemas = ["autoform", "nx", "catia", "solidworks", "autodesk", "testing"]

def greet(sqlalchemy_engine_url):
    engine = create_engine(sqlalchemy_engine_url)

    # สร้าง schemas
    with engine.begin() as conn:
        for schema_name in schemas:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    conn.commit()       
    #====================================
    # Define tables

    class nx(Base):
        __tablename__ = "session_logs"
        __table_args__ = {"schema": "nx"}
        id = Column(Integer, primary_key=True, autoincrement=True)
        start_date = Column(Date)
        start_time = Column(Time)
        end_date = Column(Date)
        end_time = Column(Time)
        duration_minutes = Column(Numeric(10,2))
        hostname = Column(String)
        module = Column(String)
        username = Column(String)

    class autoform(Base):
        __tablename__ = "session_logs"
        __table_args__ = {"schema": "autoform"}
        id = Column(Integer, primary_key=True, autoincrement=True)
        start_date = Column(Date)
        start_time = Column(Time)
        start_hours = Column(Integer)
        start_action = Column(String)
        end_date = Column(Date)
        end_time = Column(Time)
        end_hours = Column(Integer)
        end_action = Column(String)
        duration_minutes = Column(Numeric(10,2))
        host = Column(String)
        module = Column(String)
        username = Column(String)
        version = Column(String)

    class solidworks(Base):
        __tablename__ = "session_logs"
        __table_args__ = {"schema": "solidworks"}
        id = Column(Integer, primary_key=True, autoincrement=True)
        start_date = Column(Date)
        start_time = Column(Time)
        end_date = Column(Date)
        end_time = Column(Time)
        duration_minutes = Column(Numeric(10,2))
        feature = Column(String)
        username = Column(String)
        computer = Column(String)

    # สร้างทุก table
    Base.metadata.create_all(engine)
