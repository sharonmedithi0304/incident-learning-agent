from .models import Action, Incident, NewIncident

INC_1041 = Incident(
    id="INC-1041",
    title="Checkout latency spike after v3.8.2",
    service="checkout-service",
    symptom="Checkout p99 latency spiked",
    latency_s=4.8,
    deploy_version="v3.8.2",
    initial_hypothesis="database overload",
    actions=[Action(description="Increase DB capacity", outcome="FAILED",
                    note="It did not reduce checkout latency.")],
    root_cause="connection-pool exhaustion",
    successful_mitigation="roll back the connection-pool configuration",
    resolution="checkout latency returned to normal after the connection-pool rollback",
)

# Deliberately does NOT mention connection pools: only memory can point there.
INC_NEW = NewIncident(
    id="INC-1187",
    title="Checkout latency degradation after v3.9.0",
    service="checkout-service",
    symptom="Checkout p99 latency rose to 5.1s with intermittent 504s",
    latency_s=5.1,
    deploy_version="v3.9.0",
    signals=["DB CPU at 55%", "error rate 2%", "started 10 minutes after deploy"],
)

# Unrelated incident, used by tests to prove recall is relevance-based.
INC_UNRELATED = Incident(
    id="INC-0977", title="Email digest delayed", service="notification-worker",
    symptom="Weekly digest emails delayed", latency_s=0.0, deploy_version="v1.2.0",
    initial_hypothesis="SMTP provider outage",
    actions=[Action(description="Restart the mail queue", outcome="SUCCESSFUL")],
    root_cause="stuck cron scheduler", successful_mitigation="restart the cron scheduler",
    resolution="digests were delivered",
)
