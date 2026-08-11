from src.schemas.analysis import LogAnalysis


def build_retrieval_query(analysis: LogAnalysis) -> str:
    """
    Constructs a deterministic, privacy-minimized retrieval query 
    based on SSH parser findings, stripping out exact IP addresses and usernames.
    """
    concepts = set()

    # Always include baseline triage terms
    concepts.add("incident triage")
    concepts.add("evidence log preservation")

    total_failures = 0
    privileged_attempt = False
    success_after_failure = False
    multiple_accounts = False

    privileged_users = {"root", "admin", "administrator", "sysadmin"}

    for agg in analysis.ip_aggregations:
        total_failures += agg.failed_attempts

        if agg.failed_attempts > 0 and agg.successful_attempts > 0:
            success_after_failure = True

        if len(agg.users_attempted) > 1:
            multiple_accounts = True

        if any(user.lower() in privileged_users for user in agg.users_attempted):
            privileged_attempt = True

    if total_failures > 0:
        concepts.add("SSH authentication failures")
        if total_failures >= 5:
            concepts.add("repeated password attempts")

    if multiple_accounts:
        concepts.add("credential-access investigation")
        concepts.add("invalid-user login")
        concepts.add("brute force")

    if privileged_attempt:
        concepts.add("privileged-account monitoring")

    if success_after_failure:
        concepts.add("successful login after failures")

    # Sort for determinism
    return " ".join(sorted(concepts))
