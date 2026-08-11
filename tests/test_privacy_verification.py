from sqlalchemy import text
from src.database import SessionLocal
from src.models.parsed_log_line import ParsedLogLine

def test_raw_logs_never_stored_in_sqlite():
    """
    Verifies that raw security logs are NEVER stored in SQLite.
    Checks the parsed_log_lines table (if it exists) to ensure it is empty
    or at least that raw_content is not persisted.
    Also verifies incident_reports does not contain raw logs.
    """
    db = SessionLocal()
    try:
        # 1. Verify parsed_log_lines is empty or unused
        # As per privacy rules, we should not store raw logs here.
        # Our implementation parses lines in memory and aggregates them,
        # bypassing this table entirely.
        count = db.query(ParsedLogLine).count()
        assert count == 0, "parsed_log_lines table should not be populated with raw log content!"

        # 2. Check incident_reports for raw log leakage
        # (Assuming the DB has some rows from other tests)
        rows = db.execute(text("SELECT raw_model_response FROM incident_reports")).fetchall()
        for row in rows:
            content = row[0]
            # Verify the raw log line is not literally in the model response
            # (Though model responses might contain snippets, they should not dump the raw file)
            # The most direct violation would be dumping the raw log into the DB.
            assert "Failed password for root from 1.1.1.1 port 22 ssh2" not in str(content), \
                "Raw log was found stored in incident_reports!"
    finally:
        db.close()
