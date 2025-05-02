from google import genai
from google.genai import types
import json, os, pyodbc
from dotenv import load_dotenv

# load data from .env
load_dotenv()

# db configuration
DB_CONFIG = {
    "server":   os.getenv("MSSQL_SERVER"),
    "database": os.getenv("MSSQL_DATABASE"),
    "user":     os.getenv("MSSQL_USER"),
    "password": os.getenv("MSSQL_PASSWORD"),
    "port":     os.getenv("MSSQL_PORT", "1433"),
    "driver":   os.getenv("MSSQL_DRIVER", "{ODBC Driver 17 for SQL Server}"),
}

def extract_schema(db_conf):
    """
    Function that extract schema of a Database in json format
       Used to be send to AI 
    """
    conn_str = (
        f"DRIVER={db_conf['driver']};"
        f"SERVER={db_conf['server']},{db_conf['port']};"
        f"DATABASE={db_conf['database']};"
        f"UID={db_conf['user']};"
        f"PWD={db_conf['password']};"
        "Encrypt=no;TrustServerCertificate=yes;"
    )

    schema = {}

    try:
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            cur = conn.cursor()

            # ── 1. all user tables (with schema name) ─────────────────────────────
            cur.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                  AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA');
            """)
            tables = cur.fetchall()

            # ── 2. walk every table ───────────────────────────────────────────────
            for table_schema, table_name in tables:
                fq_name = f"{table_schema}.{table_name}"

                tbl_def = {
                    "schema":       table_schema,
                    "table":        table_name,
                    "columns":      [],
                    "primary_key":  [],
                    "foreign_keys": []
                }

                # 2a. columns ------------------------------------------------------
                cur.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                    ORDER BY ORDINAL_POSITION;
                """, (table_schema, table_name))
                for col in cur.fetchall():
                    tbl_def["columns"].append({
                        "name":     col.COLUMN_NAME,
                        "type":     col.DATA_TYPE,
                        "nullable": col.IS_NULLABLE == "YES",
                        "default":  col.COLUMN_DEFAULT,
                    })

                # 2b. primary key --------------------------------------------------
                cur.execute("""
                    SELECT KU.COLUMN_NAME
                    FROM   INFORMATION_SCHEMA.TABLE_CONSTRAINTS TC
                    JOIN   INFORMATION_SCHEMA.KEY_COLUMN_USAGE KU
                           ON KU.CONSTRAINT_NAME = TC.CONSTRAINT_NAME
                          AND KU.TABLE_SCHEMA   = TC.TABLE_SCHEMA
                    WHERE  TC.TABLE_SCHEMA = ?
                      AND  TC.TABLE_NAME   = ?
                      AND  TC.CONSTRAINT_TYPE = 'PRIMARY KEY';
                """, (table_schema, table_name))
                tbl_def["primary_key"] = [row.COLUMN_NAME for row in cur.fetchall()]

                # 2c. foreign keys -------------------------------------------------
                cur.execute("""
                    SELECT
                        KCU.COLUMN_NAME            AS local_column,
                        KCU2.TABLE_SCHEMA          AS ref_schema,
                        KCU2.TABLE_NAME            AS ref_table,
                        KCU2.COLUMN_NAME           AS ref_column
                    FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS RC
                    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE KCU
                          ON KCU.CONSTRAINT_NAME = RC.CONSTRAINT_NAME
                    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE KCU2
                          ON KCU2.CONSTRAINT_NAME = RC.UNIQUE_CONSTRAINT_NAME
                         AND KCU.ORDINAL_POSITION = KCU2.ORDINAL_POSITION
                    WHERE KCU.TABLE_SCHEMA = ? AND KCU.TABLE_NAME = ?;
                """, (table_schema, table_name))
                for fk in cur.fetchall():
                    tbl_def["foreign_keys"].append({
                        "local_column":     fk.local_column,
                        "referenced_table": f"{fk.ref_schema}.{fk.ref_table}",
                        "referenced_column": fk.ref_column,
                    })

                schema[fq_name] = tbl_def

    except Exception as exc:
        raise RuntimeError(f"Schema extraction failed: {exc}") from exc

    return schema

def ai_request(json_schema,user_text):
    """
    Function that make a request to AI with parameters.
    model - model of Gemini ai 
    system_instruction - Pre promt instruction given to to AI model to follow this rules
    contents - the text based promt 
    """
    try:
        client = genai.Client(api_key=os.getenv("API_KEY"))

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=f"""Act as an expert in MSSQL database. You will be given a database schema definition and a natural language question. Your task is to generate the correct MSSQL query to answer the question using *only* the provided schema and considering any provided context.

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
        {json_schema}
        ```
        """),
            contents=user_text
        )

        # print(response.text)
        return response.text
    
    except Exception as e:
        print(e)
        return e

def request_to_db(ai_response,db_conf):
    try:
        # remove the markdown formatting from the ai response
        executed_response = "{}".format(ai_response.split('```sql')[1].split('```')[0].strip())

        conn_str = (
        f"DRIVER={db_conf['driver']};"
        f"SERVER={db_conf['server']},{db_conf['port']};"
        f"DATABASE={db_conf['database']};"
        f"UID={db_conf['user']};"
        f"PWD={db_conf['password']};"
        "Encrypt=no;TrustServerCertificate=yes;"
    )
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            cur = conn.cursor()
            cur.execute(executed_response)

            # Check if it's a SELECT query
            if executed_response.strip().lower().startswith("select"):
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                # Return as list of dicts (optional, for easy JSON export)
                result = [dict(zip(columns, row)) for row in rows]
                return {"status": "success", "rows": result}
            else:
                # For INSERT/UPDATE/DELETE etc.
                affected = cur.rowcount
                return {"status": "success", "rows_affected": affected}

    except pyodbc.Error as e:
        # Handle database errors
        return {"status": "error", "message": str(e)}

    except Exception as e:
        # Handle unexpected errors
        return {"status": "error", "message": f"Unexpected error: {e}"}

def main():
    json_schema = json.dumps(extract_schema(DB_CONFIG), indent=2, ensure_ascii=False)
    ai_sql = ai_request(json_schema,user_text)
    print(f"\nThe sql query is :\n{ai_sql}")
    result = request_to_db(ai_sql, DB_CONFIG)
    print(f"\nThe database responce for query:\n{result}")

if __name__ == "__main__":
    main()