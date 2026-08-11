import datetime

from src.rag.query import build_retrieval_query
from src.schemas.analysis import IPAggregation, LogAnalysis


def test_build_retrieval_query_baseline():
    analysis = LogAnalysis(
        total_lines=10,
        unparsed_lines=0,
        start_time=None,
        end_time=None,
        ip_aggregations=[],
        limitations=[]
    )
    query = build_retrieval_query(analysis)
    assert "incident triage" in query
    assert "evidence log preservation" in query
    assert "SSH authentication failures" not in query


def test_build_retrieval_query_failures():
    agg = IPAggregation(
        ip="192.168.1.1",
        failed_attempts=3,
        successful_attempts=0,
        first_seen=datetime.datetime.now(),
        last_seen=datetime.datetime.now(),
        users_attempted=["user1"]
    )
    analysis = LogAnalysis(
        total_lines=10,
        unparsed_lines=0,
        start_time=None,
        end_time=None,
        ip_aggregations=[agg],
        limitations=[]
    )
    query = build_retrieval_query(analysis)
    assert "SSH authentication failures" in query
    assert "repeated password attempts" not in query


def test_build_retrieval_query_repeated_failures():
    agg = IPAggregation(
        ip="192.168.1.1",
        failed_attempts=10,
        successful_attempts=0,
        first_seen=datetime.datetime.now(),
        last_seen=datetime.datetime.now(),
        users_attempted=["user1"]
    )
    analysis = LogAnalysis(
        total_lines=10,
        unparsed_lines=0,
        start_time=None,
        end_time=None,
        ip_aggregations=[agg],
        limitations=[]
    )
    query = build_retrieval_query(analysis)
    assert "repeated password attempts" in query


def test_build_retrieval_query_privileged_and_success():
    agg = IPAggregation(
        ip="192.168.1.1",
        failed_attempts=2,
        successful_attempts=1,
        first_seen=datetime.datetime.now(),
        last_seen=datetime.datetime.now(),
        users_attempted=["root"]
    )
    analysis = LogAnalysis(
        total_lines=10,
        unparsed_lines=0,
        start_time=None,
        end_time=None,
        ip_aggregations=[agg],
        limitations=[]
    )
    query = build_retrieval_query(analysis)
    assert "privileged-account monitoring" in query
    assert "successful login after failures" in query


def test_build_retrieval_query_multiple_accounts_no_identifiers():
    agg = IPAggregation(
        ip="10.0.0.5",
        failed_attempts=20,
        successful_attempts=0,
        first_seen=datetime.datetime.now(),
        last_seen=datetime.datetime.now(),
        users_attempted=["alice", "bob", "charlie"]
    )
    analysis = LogAnalysis(
        total_lines=10,
        unparsed_lines=0,
        start_time=None,
        end_time=None,
        ip_aggregations=[agg],
        limitations=[]
    )
    query = build_retrieval_query(analysis)
    assert "credential-access investigation" in query
    assert "invalid-user login" in query
    assert "brute force" in query
    
    # Assert no PII/identifiers leak into query
    assert "10.0.0.5" not in query
    assert "alice" not in query
    assert "bob" not in query
    assert "charlie" not in query
