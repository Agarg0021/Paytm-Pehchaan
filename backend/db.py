from __future__ import annotations

import threading
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "pehchaan.duckdb"

_lock = threading.Lock()
_con: duckdb.DuckDBPyConnection | None = None


def connect() -> duckdb.DuckDBPyConnection:
    global _con
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _con is None:
        _con = duckdb.connect(str(DB_PATH))
        _con.execute("PRAGMA threads=1")
    return _con


def close() -> None:
    global _con
    with _lock:
        if _con is not None:
            _con.close()
            _con = None


def run(sql: str, params: list | tuple | None = None):
    with _lock:
        con = connect()
        if params is None:
            return con.execute(sql)
        return con.execute(sql, params)


def fetchall(sql: str, params: list | tuple | None = None) -> list:
    with _lock:
        con = connect()
        cur = con.execute(sql) if params is None else con.execute(sql, params)
        return cur.fetchall()


def fetchone(sql: str, params: list | tuple | None = None):
    with _lock:
        con = connect()
        cur = con.execute(sql) if params is None else con.execute(sql, params)
        return cur.fetchone()


def executemany(sql: str, rows: list) -> None:
    with _lock:
        con = connect()
        con.executemany(sql, rows)


def init_schema() -> None:
    run(
        """
        CREATE TABLE IF NOT EXISTS merchant (
            id INTEGER PRIMARY KEY,
            name TEXT,
            locality TEXT,
            city TEXT,
            salt TEXT
        );

        CREATE TABLE IF NOT EXISTS payers (
            hash TEXT PRIMARY KEY,
            cadence_mean DOUBLE,
            cadence_std DOUBLE,
            ticket_mean DOUBLE,
            persona TEXT
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY,
            payer_hash TEXT,
            amount INTEGER,
            ts TIMESTAMP,
            hour INTEGER,
            dow INTEGER,
            is_live BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS cues (
            id INTEGER PRIMARY KEY,
            payment_id INTEGER,
            payer_hash TEXT,
            cue_type TEXT,
            why_hi TEXT,
            why_en TEXT,
            ts TIMESTAMP,
            propensity DOUBLE,
            is_live BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY,
            cue_id INTEGER,
            ts TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS outcomes (
            cue_id INTEGER PRIMARY KEY,
            returned_14d BOOLEAN
        );

        CREATE TABLE IF NOT EXISTS bandit (
            cue_type TEXT PRIMARY KEY,
            pulls INTEGER,
            rewards INTEGER,
            pruned BOOLEAN,
            prune_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS model (
            intercept DOUBLE,
            w_ticket DOUBLE,
            w_hour DOUBLE,
            w_dow DOUBLE,
            w_weekend DOUBLE,
            threshold DOUBLE
        );

        CREATE TABLE IF NOT EXISTS demo_script (
            seq INTEGER PRIMARY KEY,
            payer_hash TEXT,
            amount INTEGER,
            hour INTEGER,
            expected_cue TEXT,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            k TEXT PRIMARY KEY,
            v TEXT
        );

        CREATE TABLE IF NOT EXISTS optouts (
            hash TEXT PRIMARY KEY,
            ts TIMESTAMP
        );

        CREATE SEQUENCE IF NOT EXISTS seq_payment START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_cue START 1;
        CREATE SEQUENCE IF NOT EXISTS seq_action START 1;
        """
    )
