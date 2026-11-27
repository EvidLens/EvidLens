import logging
from sqlalchemy import text
logger = logging.getLogger("evidlens.fix_fk")
def fix_workspace_fks(engine):
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT conname, conrelid::regclass::text AS tbl, a.attname AS col "
                "FROM pg_constraint c "
                "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey) "
                "WHERE c.contype = 'f' AND c.confrelid = 'user'::regclass "
                "AND conrelid::regclass::text ILIKE '%workspace%'"
            )).fetchall()
            if not rows:
                logger.info("fix_workspace_fks: no workspace FKs pointing to user found")
                return
            for conname, tbl, col in rows:
                try:
                    conn.execute(text(f'ALTER TABLE {tbl} DROP CONSTRAINT IF EXISTS {conname}'))
                    conn.commit()
                except Exception as e:
                    logger.exception(f"fix_workspace_fks drop failed {tbl}.{conname}: {e}")
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    continue
                try:
                    ref = "workspaces" if tbl != "workspaces" and col == "workspace_id" else "auth_user"
                    conn.execute(text(f'ALTER TABLE {tbl} ADD CONSTRAINT {conname} FOREIGN KEY ({col}) REFERENCES {ref}(id) ON DELETE CASCADE'))
                    conn.commit()
                    logger.info(f"fix_workspace_fks: fixed {tbl}.{conname} -> {ref}(id)")
                except Exception as e:
                    logger.exception(f"fix_workspace_fks add failed {tbl}.{conname}: {e}")
                    try:
                        conn.rollback()
                    except Exception:
                        pass
    except Exception as e:
        logger.exception(f"fix_workspace_fks failed: {e}")
