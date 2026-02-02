import pandas as pd
import psycopg2
import streamlit as st

#######################################################
# General DB functions
#######################################################
def get_conn():
    url = st.secrets["DATABASE_URL"]
    return psycopg2.connect(url)

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

            cur.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
            );
            """)

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


######################################################
# User authentication functions
#####################################################

import bcrypt

def create_user(email: str, password: str):
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO app_users(email, password_hash)
                VALUES (%s, %s)
                ON CONFLICT (email) DO UPDATE SET password_hash=EXCLUDED.password_hash;
            """, (email.lower().strip(), pw_hash))
        conn.commit()

def verify_user(email: str, password: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash, is_active FROM app_users WHERE email=%s", (email.lower().strip(),))
            row = cur.fetchone()
    if not row:
        return False
    pw_hash, is_active = row
    if not is_active:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8"))
