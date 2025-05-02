from google import genai
from google.genai import types
import json, os, mysql.connector
from dotenv import load_dotenv

# load data from .env
load_dotenv()

# db corfiguration
DB_CONFIG = {
    "host":     os.getenv("MYSQL_HOST"),
    "database": os.getenv("MYSQL_DATABASE"),
    "user":     os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "port":     os.getenv("MYSQL_PORT"),
}


def extract_schema(db_conf):
    FK_QUERY = """
        SELECT
            kcu.column_name            AS local_column,
            kcu.referenced_table_name  AS referenced_table,
            kcu.referenced_column_name AS referenced_column
        FROM information_schema.key_column_usage AS kcu
        JOIN information_schema.referential_constraints AS rc
            ON  rc.constraint_schema = kcu.constraint_schema
            AND rc.constraint_name   = kcu.constraint_name
            AND rc.table_name        = kcu.table_name
        WHERE kcu.constraint_schema = %s
        AND kcu.table_name        = %s
        AND kcu.referenced_table_name IS NOT NULL
        """
    schema = {}
    with mysql.connector.connect(**db_conf) as conn, conn.cursor(dictionary=True) as cur:
        # portable table list
        cur.execute("SHOW TABLES")
        table_col = cur.column_names[0]
        tables = [row[table_col] for row in cur]

        for tbl in tables:
            tbl_def = {"columns": [], "primary_key": [], "foreign_keys": []}

            # columns & PKs
            cur.execute(f"SHOW FULL COLUMNS FROM `{tbl}`")
            for col in cur.fetchall():
                tbl_def["columns"].append(
                    {
                        "name": col["Field"],
                        "type": col["Type"],
                        "nullable": col["Null"] == "YES",
                        "default": col["Default"],
                    }
                )
                if col["Key"] == "PRI":
                    tbl_def["primary_key"].append(col["Field"])

            # FKs
            cur.execute(FK_QUERY, (db_conf["database"], tbl))
            for fk in cur.fetchall():
                tbl_def["foreign_keys"].append(
                    {
                        "local_column": fk["local_column"],
                        "referenced_table": fk["referenced_table"],
                        "referenced_column": fk["referenced_column"],
                    }
                )

            schema[tbl] = tbl_def
    return schema

def ai_request(json_schema):

    client = genai.Client(api_key=os.getenv("API_KEY"))

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=f"""Act as an expert Text-to-SQL translator for a MySQL database. You will be given a database schema definition and a natural language question. Your task is to generate the correct MySQL query to answer the question using *only* the provided schema and considering any provided context.

    **Input Schema Details:**
    The schema is provided as a JSON object where:
    - Keys are table names.
    - Each table value is an object containing:
        - `columns`: A list of objects, each describing a column (`name`, `type`, `nullable`, `default`).
        - `primary_key`: A list of column names forming the primary key.
        - `foreign_keys`: A list of objects, each describing a foreign key relationship (`local_column`, `referenced_table`, `referenced_column`).

    ---
    **Database Schema:**

    ```json
    {json_schema}"""),
        contents="List Employees Hired in 2021"
    )

    print(response.text)

def main():
    json_schema = json.dumps(extract_schema(DB_CONFIG), indent=2, ensure_ascii=False)
    ai_request(json_schema)

if __name__ == "__main__":
    main()
