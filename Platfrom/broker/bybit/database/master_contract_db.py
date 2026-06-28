"""
Bybit Master Contract Database.

Downloads symbol/trading pair information from Bybit's public
GET /v5/market/instruments-info endpoint and stores it in the SilverTrade
symtoken table.

Symbols stored:
  - Spot trading pairs (status == "Trading")
  - Each pair becomes a "CRYPTO" exchange symbol

Field mapping (from instruments-info > list[]):
    token       ← symbol (trading pair, e.g. "BTCUSDT")
    symbol      ← baseCoin (e.g. "BTC") — SilverTrade AI canonical
    brsymbol    ← symbol (e.g. "BTCUSDT") — broker-native symbol
    name        ← baseCoin + "/" + quoteCoin
    exchange    ← "CRYPTO"
    brexchange  ← "BYBIT"
    expiry      ← "" (spot pairs don't expire)
    strike      ← 0.0
    lotsize     ← lotSizeFilter.minOrderQty or 1
    instrumenttype ← "SPOT"
    tick_size   ← priceFilter.tickSize
    contract_value ← 1.0

References:
  https://bybit-exchange.github.io/docs/v5/market/instruments-info
"""

import os
import time

import pandas as pd
from sqlalchemy import Column, Float, Index, Integer, Sequence, String, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from broker.bybit.api.baseurl import get_api_response
from extensions import socketio
from utils.logging import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=50,
    pool_timeout=30,
    pool_recycle=3600,
    connect_args={"timeout": 30, "check_same_thread": False},
)

try:
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.execute(text("PRAGMA temp_store=memory"))
        conn.execute(text("PRAGMA mmap_size=268435456"))
        conn.commit()
except Exception as e:
    logger.warning(f"Could not set SQLite pragmas for master_contract_db: {e}")

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class SymToken(Base):
    __tablename__ = "symtoken"
    id = Column(Integer, Sequence("symtoken_id_seq"), primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    brsymbol = Column(String, nullable=False, index=True)
    name = Column(String)
    exchange = Column(String, index=True)
    brexchange = Column(String, index=True)
    token = Column(String, index=True)
    expiry = Column(String)
    strike = Column(Float)
    lotsize = Column(Integer)
    instrumenttype = Column(String)
    tick_size = Column(Float)
    contract_value = Column(Float, default=1.0)

    __table_args__ = (Index("idx_symbol_exchange", "symbol", "exchange"),)


def init_db():
    """Initialize the master contract database table."""
    logger.info("Initializing Bybit Master Contract DB")
    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import inspect as sa_inspect

        insp = sa_inspect(engine)
        existing_cols = {c["name"] for c in insp.get_columns("symtoken")}
        if "contract_value" not in existing_cols:
            with engine.connect() as conn:
                conn.execute(
                    text("ALTER TABLE symtoken ADD COLUMN contract_value REAL DEFAULT 1.0")
                )
                conn.commit()
                logger.info("Migrated symtoken table: added contract_value column")
    except Exception as e:
        logger.error(f"contract_value migration failed: {e}")


def delete_symtoken_table():
    """Delete all records from the symtoken table."""
    logger.info("Deleting Symtoken Table")
    SymToken.query.delete()
    db_session.commit()


def copy_from_dataframe(df):
    """Bulk insert from DataFrame into symtoken table."""
    logger.info("Performing Bulk Insert")
    data_dict = df.to_dict(orient="records")

    try:
        from sqlalchemy import inspect as sa_inspect

        _db_cols = {c["name"] for c in sa_inspect(engine).get_columns("symtoken")}
    except Exception:
        _db_cols = None

    if _db_cols is not None and data_dict:
        extra_cols = {k for k in data_dict[0] if k not in _db_cols}
        if extra_cols:
            logger.warning(f"Stripping unknown columns: {extra_cols}")
            data_dict = [{k: v for k, v in row.items() if k not in extra_cols} for row in data_dict]

    existing_tokens = {result.token for result in db_session.query(SymToken.token).all()}
    filtered_data = [row for row in data_dict if row["token"] not in existing_tokens]

    chunk_size = 500
    total_inserted = 0

    try:
        if filtered_data:
            logger.info(f"Starting bulk insert of {len(filtered_data)} records")
            for i in range(0, len(filtered_data), chunk_size):
                chunk = filtered_data[i : i + chunk_size]
                try:
                    db_session.bulk_insert_mappings(SymToken, chunk)
                    db_session.commit()
                    total_inserted += len(chunk)
                    if (i // chunk_size + 1) % 20 == 0:
                        logger.debug(f"Processed {total_inserted} records so far...")
                except Exception as chunk_error:
                    logger.warning(
                        f"Error inserting chunk {i // chunk_size + 1}, retrying: {chunk_error}"
                    )
                    db_session.rollback()
                    try:
                        time.sleep(0.1)
                        db_session.bulk_insert_mappings(SymToken, chunk)
                        db_session.commit()
                        total_inserted += len(chunk)
                    except Exception:
                        db_session.rollback()
                        continue
                time.sleep(0.005)
            logger.info(f"Bulk insert completed with {total_inserted} new records.")
        else:
            logger.info("No new records to insert.")
    except Exception as e:
        logger.exception(f"Error during bulk insert: {e}")
        db_session.rollback()


def fetch_bybit_symbols():
    """
    Fetch all trading pairs from Bybit GET /v5/market/instruments-info.

    Bybit uses cursor-based pagination (nextPageCursor).
    Filter: category=spot, status=Trading

    Returns:
        Tuple of (list of symbol dicts, bool success)
    """
    all_symbols = []
    cursor = None
    max_pages = 20

    for page in range(max_pages):
        params = {"category": "spot", "limit": 1000}
        if cursor:
            params["cursor"] = cursor

        result = get_api_response("/v5/market/instruments-info", params=params)
        if not result.get("success"):
            error = result.get("error", {})
            logger.error(f"Failed to fetch instruments-info (page {page + 1}): {error}")
            return all_symbols, False

        data = result.get("result", {})
        symbols = data.get("list", [])
        if isinstance(symbols, list):
            # Only include Trading status symbols
            for s in symbols:
                if isinstance(s, dict) and s.get("status") == "Trading":
                    all_symbols.append(s)

        cursor = data.get("nextPageCursor")
        if not cursor:
            break

    logger.info(f"Fetched {len(all_symbols)} Trading symbols from Bybit instruments-info")
    return all_symbols, True


def process_bybit_symbols(symbols):
    """
    Convert a list of Bybit instrument info dicts to a DataFrame.

    Bybit spot instrument fields:
        symbol         – trading pair (e.g. "BTCUSDT")
        baseCoin       – base asset (e.g. "BTC")
        quoteCoin      – quote asset (e.g. "USDT")
        status         – "Trading" | "PreLaunch" | etc.
        lotSizeFilter  – { "basePrecision": "0.000001", "quotePrecision": "0.01",
                           "minOrderQty": "0.000001", "maxOrderQty": "1000", ... }
        priceFilter    – { "tickSize": "0.01", "minPrice": "0.01", "maxPrice": "1000000" }
    """
    if not symbols:
        logger.error("No symbols to process")
        return pd.DataFrame()

    rows = []
    for s in symbols:
        symbol = s.get("symbol", "")
        base_coin = s.get("baseCoin", "")
        quote_coin = s.get("quoteCoin", "")

        if not symbol or not base_coin:
            continue

        # Extract filters
        lot_filter = s.get("lotSizeFilter", {}) or {}
        price_filter = s.get("priceFilter", {}) or {}

        try:
            tick_size = float(price_filter.get("tickSize", "0.01"))
        except (ValueError, TypeError):
            tick_size = 0.01

        try:
            min_qty_str = lot_filter.get("minOrderQty", "0.000001")
            lotsize = float(min_qty_str)
        except (ValueError, TypeError):
            lotsize = 0.000001

        # Convert to int if it's a whole number (for contracts), keep float for fractional
        if lotsize == int(lotsize):
            lotsize_int = int(lotsize)
        else:
            lotsize_int = lotsize

        rows.append(
            {
                "token": symbol,
                "symbol": base_coin,
                "brsymbol": symbol,
                "name": f"{base_coin}/{quote_coin}",
                "exchange": "CRYPTO",
                "brexchange": "BYBIT",
                "expiry": "",
                "strike": 0.0,
                "lotsize": lotsize_int,
                "instrumenttype": "SPOT",
                "tick_size": tick_size,
                "contract_value": 1.0,
            }
        )

    if not rows:
        logger.error("No TRADING spot symbols found in Bybit instruments-info")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["token"], keep="first")
    logger.info(f"Processed {len(df)} Bybit spot trading pairs")
    return df


def master_contract_download():
    """Download and store Bybit master contract data from instruments-info."""
    logger.info("Downloading Master Contract from Bybit")

    try:
        symbols, fetch_success = fetch_bybit_symbols()

        if not symbols:
            return socketio.emit(
                "master_contract_download",
                {"status": "error", "message": "No symbols returned from Bybit instruments-info"},
            )

        if not fetch_success:
            return socketio.emit(
                "master_contract_download",
                {
                    "status": "error",
                    "message": "Failed to fetch symbols from Bybit. Existing master contract preserved.",
                },
            )

        token_df = process_bybit_symbols(symbols)

        if token_df.empty:
            return socketio.emit(
                "master_contract_download",
                {"status": "error", "message": "No TRADING spot symbols found on Bybit"},
            )

        delete_symtoken_table()
        copy_from_dataframe(token_df)

        return socketio.emit(
            "master_contract_download",
            {
                "status": "success",
                "message": f"Successfully Downloaded {len(token_df)} Bybit Trading Pairs",
            },
        )

    except Exception as e:
        logger.exception(f"Error during Bybit master contract download: {e}")
        return socketio.emit("master_contract_download", {"status": "error", "message": str(e)})


def search_symbols(symbol, exchange):
    """Search for symbols in the database."""
    return SymToken.query.filter(
        SymToken.symbol.like(f"%{symbol}%"),
        SymToken.exchange == exchange,
    ).all()
