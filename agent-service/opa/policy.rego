package rca

import rego.v1

# ─────────────────────────────────────────────────────────────────────────────
#  OPA Policy: rca/allow
#
#  Input shape:
#    { "issue_type": "...", "environment": "...", "confidence": 0.0–1.0 }
#
#  Result: true  → orchestrator proceeds to Fixer
#          false → alert_only, no remediation
# ─────────────────────────────────────────────────────────────────────────────

default allow := false

# Valid issue types from the rulebook
valid_issue_types := {
    "cpu_high",
    "memory_high",
    "disk_high",
    "service_error_log",
    "log_issue",
    "kubernetes_pod_crash"
}

# Valid execution environments
valid_environments := {
    "kubernetes",
    "docker",
    "systemd",
    "host"
}

# Minimum confidence for auto-remediation
min_confidence := 0.5

# Main allow rule
allow if {
    input.issue_type != "none"
    valid_issue_types[input.issue_type]
    valid_environments[input.environment]
    input.confidence >= min_confidence
}

# Deny reason helpers
deny_reason := "issue_type not in rulebook" if {
    not valid_issue_types[input.issue_type]
}

deny_reason := "environment not valid" if {
    valid_issue_types[input.issue_type]
    not valid_environments[input.environment]
}

deny_reason := "confidence below threshold" if {
    valid_issue_types[input.issue_type]
    valid_environments[input.environment]
    input.confidence < min_confidence
}
