"""
Binance Master Contract Database.

Downloads symbol/trading pair information from Binance's public
GET /api/v3/exchangeInfo endpoint and stores it in the SilverTrade
symtoken table for use by order placement and market data services.

Symbols stored:
  - Spot trading pairs (status == "TRADING")
  - Each pair becomes a "CRYPTO" exchange symbol

Field mapping (from exchangeInfo > symbols[]):
    token       ← symbol (trading pair, e.g. "BTCUSDT")
    symbol      ← baseAsset (e.g. "BTC") — SilverTrade AI canonical
    brsymbol    ← symbol (e.g. "BTCUSDT") — broker-native symbol
    name        ← baseAsset + "/" + quoteAsset
    exchange    ← "CRYPTO"
    brexchange  ← "BINANCE"
    expiry      ← "" (spot pairs don't expire)
    strike      ← 0.0
    lotsize     ← lot_size or 1
    instrumenttype ← "SPOT" (or "PERPFUT" for futures in future enhancement)
    tick_size   ← from filters
    contract_value ← 1.0

References:
  https://binance-docs.github.io/apidocs/spot/en/#exchange-information
"""

import os
import time

import pandas as pd
from sqlalchemy import Column, Float, Index, Integer, Sequence, String, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from broker.binance.api.baseurl import get_api_response
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

# Enable WAL mode
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
    logger.info("Initializing Binance Master Contract DB")
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

    # Determine which columns exist in the DB
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

    # Filter out existing tokens
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
                    except Exception as retry_error:
                        logger.error(f"Failed chunk {i // chunk_size + 1}: {retry_error}")
                        db_session.rollback()
                        continue
                time.sleep(0.005)
            logger.info(f"Bulk insert completed with {total_inserted} new records.")
        else:
            logger.info("No new records to insert.")
    except Exception as e:
        logger.exception(f"Error during bulk insert: {e}")
        db_session.rollback()


def _extract_filter_value(filters, filter_type, field_name, default=None):
    """Extract a field value from exchangeInfo filters list."""
    for f in filters:
        if f.get("filterType") == filter_type:
            return f.get(field_name, default)
    return default


def fetch_binance_symbols():
    """
    Fetch all trading pairs from Binance GET /api/v3/exchangeInfo.

    Returns:
        Tuple of (list of symbol dicts, bool success)
    """
    try:
        result = get_api_response("/api/v3/exchangeInfo")
        if not result.get("success"):
            error = result.get("error", {})
            logger.error(f"Failed to fetch exchangeInfo: {error}")
            return [], False

        data = result.get("result", {})
        symbols = data.get("symbols", [])
        logger.info(f"Fetched {len(symbols)} symbols from Binance exchangeInfo")
        return symbols, True

    except Exception as e:
        logger.error(f"Exception fetching exchangeInfo: {e}")
        return [], False


def process_binance_symbols(symbols):
    """
    Convert a list of Binance symbol dicts to a DataFrame matching SymToken schema.

    Field mapping:
        token        ← symbol (trading pair, e.g. "BTCUSDT")
        symbol       ← baseAsset (e.g. "BTC")
        brsymbol     ← symbol (e.g. "BTCUSDT")
        name         ← baseAsset + "/" + quoteAsset
        exchange     ← "CRYPTO"
        brexchange   ← "BINANCE"
        expiry       ← ""
        strike       ← 0.0
        lotsize      ← lot_size from filters
        instrumenttype ← "SPOT"
        tick_size    ← tickSize from filters
        contract_value ← 1.0

    Args:
        symbols: List of symbol dicts from exchangeInfo

    Returns:
        DataFrame with columns matching SymToken schema
    """
    if not symbols:
        logger.error("No symbols to process")
        return pd.DataFrame()

    rows = []
    for s in symbols:
        # Only include TRADING status symbols
        if s.get("status") != "TRADING":
            continue

        # Only include SPOT symbols
        if s.get("isSpotTradingAllowed") is False:
            continue

        symbol = s.get("symbol", "")
        base_asset = s.get("baseAsset", "")
        quote_asset = s.get("quoteAsset", "")

        if not symbol or not base_asset:
            continue

        # Extract filters
        filters = s.get("filters", [])
        tick_size = _extract_filter_value(filters, "PRICE_FILTER", "tickSize", "0.01")
        lot_size = _extract_filter_value(filters, "LOT_SIZE", "stepSize", "1")

        try:
            lotsize = float(lot_size) if "." in str(lot_size) else int(float(lot_size))
        except (ValueError, TypeError):
            lotsize = 1

        try:
            tick_size_f = float(tick_size)
        except (ValueError, TypeError):
            tick_size_f = 0.01

        rows.append(
            {
                "token": symbol,
                "symbol": base_asset,
                "brsymbol": symbol,
                "name": f"{base_asset}/{quote_asset}",
                "exchange": "CRYPTO",
                "brexchange": "BINANCE",
                "expiry": "",
                "strike": 0.0,
                "lotsize": int(lotsize)
                if isinstance(lotsize, float) and lotsize.is_integer()
                else lotsize,
                "instrumenttype": "SPOT",
                "tick_size": tick_size_f,
                "contract_value": 1.0,
            }
        )

    if not rows:
        logger.error("No TRADING spot symbols found in Binance exchangeInfo")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["token"], keep="first")
    logger.info(f"Processed {len(df)} Binance spot trading pairs")
    return df


def master_contract_download():
    """
    Download and store Binance master contract data from exchangeInfo.
    """
    logger.info("Downloading Master Contract from Binance")

    try:
        symbols, fetch_success = fetch_binance_symbols()

        if not symbols:
            return socketio.emit(
                "master_contract_download",
                {"status": "error", "message": "No symbols returned from Binance exchangeInfo"},
            )

        if not fetch_success:
            return socketio.emit(
                "master_contract_download",
                {
                    "status": "error",
                    "message": "Failed to fetch symbols from Binance. Existing master contract preserved.",
                },
            )

        token_df = process_binance_symbols(symbols)

        if token_df.empty:
            return socketio.emit(
                "master_contract_download",
                {"status": "error", "message": "No TRADING symbols found on Binance"},
            )

        delete_symtoken_table()
        copy_from_dataframe(token_df)

        return socketio.emit(
            "master_contract_download",
            {
                "status": "success",
                "message": f"Successfully Downloaded {len(token_df)} Binance Trading Pairs",
            },
        )

    except Exception as e:
        logger.exception(f"Error during Binance master contract download: {e}")
        return socketio.emit("master_contract_download", {"status": "error", "message": str(e)})


def search_symbols(symbol, exchange):
    """
    Search for symbols in the database.
    """
    return SymToken.query.filter(
        SymToken.symbol.like(f"%{symbol}%"),
        SymToken.exchange == exchange,
    ).all()
