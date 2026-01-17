# import os
# import sqlite3
# from typing import Dict, List, Tuple
# import pandas as pd

# DB_PATH = os.path.join("data", "finance.db")

# def _connect():
#     os.makedirs("data", exist_ok=True)
#     return sqlite3.connect(DB_PATH, check_same_thread=False)

# def init_db():
#     con = _connect()
#     cur = con.cursor()

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS monthly_lines (
#         month TEXT NOT NULL,
#         line_type TEXT NOT NULL,       -- 'income' or 'expense'
#         category TEXT NOT NULL,
#         amount REAL NOT NULL DEFAULT 0,
#         PRIMARY KEY (month, line_type, category)
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS settings (
#         key TEXT PRIMARY KEY,
#         value TEXT NOT NULL
#     )
#     """)

#     cur.execute("""
#     CREATE TABLE IF NOT EXISTS monthly_fx (
#         month TEXT PRIMARY KEY,
#         rub_to_eur REAL NOT NULL
#     )
#     """)

    


#     # Defaults
#     defaults = {
#         "starting_savings": "0",
#         "expense_categories": "food,rent,subscriptions,house,phone,clothes",
#         "income_categories": "salary_barcelona,salary_moscow,other_income",
#         "app_passcode_enabled": "0",
#         "app_passcode": "",
#     }
#     for k, v in defaults.items():
#         cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (k, v))

#     con.commit()
#     con.close()

# def get_settings() -> Dict[str, str]:
#     con = _connect()
#     df = pd.read_sql_query("SELECT key, value FROM settings", con)
#     con.close()
#     return dict(zip(df["key"], df["value"]))

# def get_or_create_settings() -> Dict[str, str]:
#     init_db()
#     return get_settings()

# def set_setting(key: str, value: str) -> None:
#     con = _connect()
#     cur = con.cursor()
#     cur.execute("INSERT INTO settings(key, value) VALUES(?, ?) "
#                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
#     con.commit()
#     con.close()

# def list_months() -> List[str]:
#     con = _connect()
#     df = pd.read_sql_query("SELECT DISTINCT month FROM monthly_lines ORDER BY month", con)
#     con.close()
#     return df["month"].tolist()

# def upsert_month_lines(month: str, line_type: str, lines: List[Tuple[str, float]]) -> None:
#     """
#     lines: list of (category, amount)
#     """
#     con = _connect()
#     cur = con.cursor()
#     for category, amount in lines:
#         cur.execute("""
#             INSERT INTO monthly_lines(month, line_type, category, amount)
#             VALUES(?, ?, ?, ?)
#             ON CONFLICT(month, line_type, category)
#             DO UPDATE SET amount=excluded.amount
#         """, (month, line_type, category, float(amount)))
#     con.commit()
#     con.close()

# def delete_month(month: str) -> None:
#     con = _connect()
#     cur = con.cursor()
#     cur.execute("DELETE FROM monthly_lines WHERE month=?", (month,))
#     con.commit()
#     con.close()

# def load_month_lines(month: str) -> pd.DataFrame:
#     con = _connect()
#     df = pd.read_sql_query(
#         "SELECT month, line_type, category, amount FROM monthly_lines WHERE month=?",
#         con, params=(month,)
#     )
#     con.close()
#     return df

# def load_all_lines() -> pd.DataFrame:
#     con = _connect()
#     df = pd.read_sql_query(
#         "SELECT month, line_type, category, amount FROM monthly_lines ORDER BY month",
#         con
#     )
#     con.close()
#     return df

# def upsert_fx_rate(month: str, rub_to_eur: float) -> None:
#     con = _connect()
#     cur = con.cursor()
#     cur.execute("""
#         INSERT INTO monthly_fx(month, rub_to_eur)
#         VALUES(?, ?)
#         ON CONFLICT(month) DO UPDATE SET rub_to_eur=excluded.rub_to_eur
#     """, (month, float(rub_to_eur)))
#     con.commit()
#     con.close()

# def get_fx_rate(month: str):
#     con = _connect()
#     df = pd.read_sql_query("SELECT rub_to_eur FROM monthly_fx WHERE month=?", con, params=(month,))
#     con.close()
#     if df.empty:
#         return None
#     return float(df["rub_to_eur"].iloc[0])

# def load_all_fx() -> pd.DataFrame:
#     con = _connect()
#     df = pd.read_sql_query("SELECT month, rub_to_eur FROM monthly_fx ORDER BY month", con)
#     con.close()
#     return df

import pandas as pd
import psycopg2
import streamlit as st

def get_conn():
    # You will set this in Streamlit Secrets on the Cloud
    # Example: postgresql://user:pass@host:5432/db?sslmode=require
    url = st.secrets["DATABASE_URL"]
    return psycopg2.connect(url)

def get_or_create_settings() -> dict:
    """
    Ensures required settings exist in the DB (with defaults) and returns settings dict.
    This preserves compatibility with older code that imports get_or_create_settings().
    """
    defaults = {
        "starting_savings": "0",
        "expense_categories": "Rent,Groceries,Transport,Utilities,Other",
        "income_categories": "Salary,Other_income",
    }

    existing = get_settings()

    # Insert any missing keys
    for k, v in defaults.items():
        if k not in existing:
            upsert_setting(k, v)

    # Return fresh merged settings
    return get_settings()

def set_setting(key: str, value: str):
    return upsert_setting(key, value)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS monthly_lines (
                month TEXT NOT NULL,
                line_type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (month, line_type, category)
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS monthly_fx (
                month TEXT PRIMARY KEY,
                rub_to_eur DOUBLE PRECISION NOT NULL
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_plan (
                day TEXT PRIMARY KEY,
                anna_drop_off TEXT NOT NULL DEFAULT '',
                anna_pick_up  TEXT NOT NULL DEFAULT '',
                other_plans   TEXT NOT NULL DEFAULT '',
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """)

        conn.commit()

def get_settings() -> dict:
    with get_conn() as conn:
        df = pd.read_sql("SELECT key, value FROM settings", conn)
    return dict(zip(df["key"], df["value"]))

def upsert_setting(key: str, value: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (key, value))
        conn.commit()

def upsert_month_lines(month: str, line_type: str, lines: list[tuple[str, float]]):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM monthly_lines WHERE month=%s AND line_type=%s", (month, line_type))
            cur.executemany("""
                INSERT INTO monthly_lines (month, line_type, category, amount)
                VALUES (%s, %s, %s, %s)
            """, [(month, line_type, cat, float(amt)) for cat, amt in lines])
        conn.commit()

def load_month_lines(month: str) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql(
            "SELECT month, line_type, category, amount FROM monthly_lines WHERE month=%s",
            conn,
            params=(month,)
        )

def load_all_lines() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql("SELECT month, line_type, category, amount FROM monthly_lines", conn)

def upsert_fx_rate(month: str, rub_to_eur: float):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO monthly_fx (month, rub_to_eur)
                VALUES (%s, %s)
                ON CONFLICT (month) DO UPDATE SET rub_to_eur = EXCLUDED.rub_to_eur
            """, (month, float(rub_to_eur)))
        conn.commit()

def get_fx_rate(month: str):
    with get_conn() as conn:
        df = pd.read_sql("SELECT rub_to_eur FROM monthly_fx WHERE month=%s", conn, params=(month,))
    return None if df.empty else float(df.iloc[0]["rub_to_eur"])

def load_all_fx() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql("SELECT month, rub_to_eur FROM monthly_fx", conn)

######################################################
# Weekly Plan DB functions
#####################################################

def load_weekly_plan() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql("""
            SELECT
                day AS "Day",
                anna_drop_off AS "Anna drop off",
                anna_pick_up  AS "Anna pick up",
                other_plans   AS "Other plans"
            FROM weekly_plan
            ORDER BY CASE day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                ELSE 99 END;
        """, conn)

    # If table is empty for some reason, return default
    if df.empty:
        return pd.DataFrame({
            "Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "Anna drop off": [""] * 5,
            "Anna pick up": [""] * 5,
            "Other plans": [""] * 5,
        })

    return df


def upsert_weekly_plan(df: pd.DataFrame) -> None:
    # df must have columns: Day, Anna drop off, Anna pick up, Other plans
    with get_conn() as conn:
        with conn.cursor() as cur:
            for _, r in df.iterrows():
                cur.execute("""
                    INSERT INTO weekly_plan(day, anna_drop_off, anna_pick_up, other_plans, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (day) DO UPDATE SET
                        anna_drop_off = EXCLUDED.anna_drop_off,
                        anna_pick_up  = EXCLUDED.anna_pick_up,
                        other_plans   = EXCLUDED.other_plans,
                        updated_at    = NOW();
                """, (
                    r["Day"],
                    str(r["Anna drop off"] or ""),
                    str(r["Anna pick up"] or ""),
                    str(r["Other plans"] or ""),
                ))
        conn.commit()


def clear_weekly_plan() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE weekly_plan
                SET anna_drop_off = '',
                    anna_pick_up  = '',
                    other_plans   = '',
                    updated_at    = NOW();
            """)
        conn.commit()
