from sqlalchemy import Column, Integer, String, Date, DateTime, create_engine, text, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
import os

# Define the database URL
# Assuming the database name is "SOS".
engine_url_sos = "postgresql://itsupport:aapico@10.10.3.215:5432/SOS"

engine_sos = create_engine(engine_url_sos)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine_sos)

class BulkOpsMixin(object):
    """
    Mixin for bulk insert and upsert operations.
    """
    
    @classmethod
    def _chunked(cls, iterable, size):
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]

    @classmethod
    def save(cls, payload: list[dict], chunk_size: int = 600) -> dict:
        """
        Public method for bulk upsert.
        """
        if not payload:
            return {"success": True, "inserted": 0, "skipped": 0}

        if not hasattr(cls, 'UPSERT_INDEX') or not cls.UPSERT_INDEX:
             raise ValueError(f"{cls.__name__}.UPSERT_INDEX is not defined")

        # Get column objects for the conflict target
        # We need the actual Column objects for index_elements
        # cls.__table__.c.column_name gives the column object
        index_cols = [cls.__table__.c[col] for col in cls.UPSERT_INDEX]
        
        with Session() as session:
            try:
                total_inserted = 0
                for batch in cls._chunked(payload, chunk_size):
                    stmt = insert(cls).values(batch)
                    
                    # Determine columns to update
                    # We update columns that are present in the payload (using the first item as reference)
                    # and are not ID or created_at.
                    if batch:
                        sample_keys = batch[0].keys()
                        update_columns = [
                            key for key in sample_keys 
                            if key not in ['id', 'created_at'] and key in cls.__table__.c
                        ]
                        
                        if update_columns:
                            set_dict = {key: getattr(stmt.excluded, key) for key in update_columns}
                            stmt = stmt.on_conflict_do_update(
                                index_elements=index_cols,
                                set_=set_dict
                            )
                        else:
                            # If no columns to update, just do nothing on conflict
                            stmt = stmt.on_conflict_do_nothing(index_elements=index_cols)

                    result = session.execute(stmt)
                    total_inserted += result.rowcount or 0
                
                session.commit()
                return {
                    "success": True,
                    "inserted": total_inserted,
                    "message": "Data upsert successfully"
                }
            except SQLAlchemyError as e:
                session.rollback()
                print(f"❌ Error during upsert: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

class Holiday(Base, BulkOpsMixin):
    __tablename__ = "holidays"
    __table_args__ = {"schema": "public"} 

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False, comment="Date of the holiday")
    name = Column(String, nullable=False, comment="Name or description of the holiday")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Define columns to use for conflict detection (ON CONFLICT)
    UPSERT_INDEX = ["date"]

    @classmethod
    def delete(cls, dates: list[Date]) -> dict:
        """
        Delete holidays by a list of dates.
        """
        if not dates:
             return {"success": True, "deleted": 0, "message": "No dates provided to delete"}
        
        with Session() as session:
            try:
                # Assuming 'date' is the column object from the class
                stmt = delete(cls).where(cls.date.in_(dates))
                result = session.execute(stmt)
                session.commit()
                return {
                    "success": True,
                    "deleted": result.rowcount or 0,
                    "message": "Data deleted successfully"
                }
            except SQLAlchemyError as e:
                session.rollback()
                print(f"❌ Error during delete: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

    @classmethod
    def get_by_range(cls, start_date: Date = None, end_date: Date = None):
        """
        Get holidays with optional date range filter
        """
        with Session() as session:
            try:
                query = session.query(cls)
                
                if start_date:
                    query = query.filter(cls.date >= start_date)
                if end_date:
                    query = query.filter(cls.date <= end_date)
                
                # Order by date
                results = query.order_by(cls.date).all()
                
                return [
                    {
                        "id": r.id, 
                        "date": r.date, 
                        "name": r.name, 
                        "created_at": r.created_at
                    }
                    for r in results
                ]
            except Exception as e:
                print(f"❌ Error fetching holidays: {e}")
                raise

def init_db():
    """Create tables if they don't exist"""
    try:
        # Check connection implicitly by creating tables
        Base.metadata.create_all(engine_sos)
        print("✅ Tables created successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

# Initialize tables when script is run directly
init_db()
