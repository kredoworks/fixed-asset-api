"""Database utilities for constructing connection URLs dynamically"""
from typing import Optional


def get_database_url(
    driver: str,
    host: str,
    port: int,
    user: str,
    password: str,
    name: str,
) -> str:
    """
    Construct database URL from components.
    
    Args:
        driver: Database driver (e.g., 'postgresql+asyncpg', 'mysql+aiomysql')
        host: Database host
        port: Database port
        user: Database user
        password: Database password
        name: Database name
    
    Returns:
        Complete database URL string
    
    Example:
        >>> get_database_url("postgresql+asyncpg", "localhost", 5432, "user", "pass", "mydb")
        'postgresql+asyncpg://user:pass@localhost:5432/mydb'
    """
    return f"{driver}://{user}:{password}@{host}:{port}/{name}"
