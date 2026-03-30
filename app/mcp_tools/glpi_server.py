import os
import mysql.connector
from mysql.connector import Error
from .router_core import MCPRouter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DB_HOST = os.getenv("GLPI_DB_HOST", "10.10.10.181")
DB_USER = os.getenv("GLPI_DB_USER", "wajeepradit.p")
DB_PASSWORD = os.getenv("GLPI_DB_PASSWORD", "Az_123456")
DB_NAME = os.getenv("GLPI_DB_NAME", "glpi")
DB_PORT = int(os.getenv("GLPI_DB_PORT", 3306))

# Initialize MCP Router
router = MCPRouter("GLPI")

def get_db_connection():
    """Establishes a connection to the GLPI MySQL database."""
    print("DEBUG: Attempting to connect to DB...")
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            connection_timeout=5,
            use_pure=True
        )
        if connection.is_connected():
            print("DEBUG: Connected!")
            return connection
    except Error as e:
        print(f"DEBUG: MySQL Error: {repr(e)}")
        raise RuntimeError(f"Error connecting to MySQL Database: {repr(e)}")
    except Exception as e:
        print(f"DEBUG: General Error: {repr(e)}")
        raise
    return None

@router.tool()
def list_tables() -> str:
    """Lists all tables in the GLPI database, useful for exploring the schema."""
    conn = get_db_connection()
    if not conn:
        return "Failed to connect to database."
    
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        result = [table[0] for table in tables]
        return "Tables in GLPI Database:\n" + "\n".join(result)
    except Error as e:
        return f"Error listing tables: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@router.tool()
def describe_table(table_name: str) -> str:
    """Shows the schema (columns, types) of a specific table in the GLPI database.
    
    Args:
        table_name: The name of the table to describe (e.g., 'glpi_computers').
    """
    conn = get_db_connection()
    if not conn:
        return "Failed to connect to database."
    
    try:
        cursor = conn.cursor()
        # Parameterized query to prevent injection in table name is tricky in SHOW COLUMNS 
        # but mysql connector usually handles simple strings safely or we can validate.
        # For simplicity in this demo, we'll try to quote it or trust the user agent context.
        # But cleaning strict characters is better.
        clean_table_name = "".join(c for c in table_name if c.isalnum() or c == '_')
        if clean_table_name != table_name:
             return "Invalid table name. Only alphanumeric and underscores allowed."
             
        cursor.execute(f"DESCRIBE {clean_table_name}")
        columns = cursor.fetchall()
        
        # Format output
        output = [f"Schema for {table_name}:"]
        output.append(f"{'Field':<30} {'Type':<20} {'Null':<10} {'Key':<10} {'Default':<10}")
        output.append("-" * 80)
        
        for col in columns:
            # Field, Type, Null, Key, Default, Extra
            field, dtype, null, key, default, extra = col
            default_val = str(default) if default is not None else "NULL"
            output.append(f"{field:<30} {dtype:<20} {null:<10} {key:<10} {default_val:<10}")
            
        return "\n".join(output)
    except Error as e:
        return f"Error describing table: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@router.tool()
def run_select_query(query: str) -> str:
    """Executes a SELECT SQL query against the GLPI database. 
    Only SELECT statements are allowed for safety.
    
    Args:
        query: The SQL SELECT query to execute.
    """
    if not query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."

    conn = get_db_connection()
    if not conn:
        return "Failed to connect to database."
        
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            return "No results found."
            
        # Format as string (or JSON string)
        import json
        # Using default=str to handle datetime objects etc
        return json.dumps(rows, default=str, indent=2)
        
    except Error as e:
        return f"SQL Error: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    mcp.run()
