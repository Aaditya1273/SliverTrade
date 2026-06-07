"""
Helper module for database initialization with better logging
Handles Postgres index re-creation gracefully (CREATE INDEX on existing tables
fails with "relation already exists" since SQLAlchemy's checkfirst only guards
table creation, not index creation).
"""

from sqlalchemy import inspect
from sqlalchemy.exc import ProgrammingError


def init_db_with_logging(base, engine, db_name, logger):
    """
    Initialize database tables with detailed logging.

    Args:
        base: SQLAlchemy Base (declarative_base)
        engine: SQLAlchemy engine
        db_name: Name of the database (for logging)
        logger: Logger instance

    Returns:
        tuple: (tables_created, tables_verified)
    """
    # Get inspector to check existing tables
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Get tables defined in this model
    model_tables = set(base.metadata.tables.keys())

    # Find which tables need to be created
    tables_to_create = model_tables - existing_tables
    tables_already_exist = model_tables & existing_tables

    # Create tables (only creates missing ones)
    try:
        base.metadata.create_all(bind=engine)
    except ProgrammingError as e:
        err_msg = str(e).lower()
        # Postgres raises ProgrammingError when CREATE INDEX fails because the
        # index already exists. SQLAlchemy's checkfirst=True only guards table
        # creation, not index creation — so on restart the indexes defined in
        # __table_args__ trigger "relation already exists".
        if "already exists" in err_msg or "duplicate" in err_msg:
            logger.warning(
                f"{db_name}: Some indexes already exist (expected on restart) — continuing"
            )
        else:
            raise

    # Log appropriately
    if tables_to_create:
        logger.debug(
            f"{db_name}: Created {len(tables_to_create)} new table(s): {', '.join(sorted(tables_to_create))}"
        )

    if tables_already_exist:
        logger.debug(f"{db_name}: Verified {len(tables_already_exist)} existing table(s)")

    if not tables_to_create and tables_already_exist:
        logger.debug(f"{db_name}: Connection verified ({len(tables_already_exist)} table(s) ready)")

    return len(tables_to_create), len(tables_already_exist)
