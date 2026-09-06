from sqlalchemy import text

from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        if db.get_bind().dialect.name != "postgresql":
            raise RuntimeError("Policy vector verification requires PostgreSQL")
        extension = db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
        if extension != 1:
            raise RuntimeError("pgvector extension is not installed")
        column_type = db.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                WHERE c.relname = 'policy_chunks' AND a.attname = 'embedding'
                """
            )
        ).scalar_one()
        if column_type != "vector(64)":
            raise RuntimeError(f"Expected vector(64), got {column_type}")
        zeros = ",".join("0" for _ in range(64))
        ones = ",".join("1" if index == 0 else "0" for index in range(64))
        distance = db.execute(
            text("SELECT CAST(:left AS vector) <=> CAST(:right AS vector)"),
            {"left": f"[{zeros}]", "right": f"[{ones}]"},
        ).scalar_one()
        if distance is None:
            raise RuntimeError("pgvector cosine-distance operator did not return a value")
        print(f"PASS: pgvector extension, vector(64) storage and cosine operator; distance={distance}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
