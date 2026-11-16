#!/usr/bin/env bash
# Creates the Sentio topics. Safe to run several times: existing topics are left unchanged.
# Runs inside the redpanda-init container; rpk reads the addresses from RPK_BROKERS and RPK_ADMIN_HOSTS.
set -euo pipefail

TOPICS=(
  conversations.raw      # simulator -> enrichment
  conversations.enriched # enrichment -> api-worker / api-server
  conversations.dlq      # events that could not be parsed or processed
)

# Topics must be created on purpose: a typo in a topic name must fail instead of creating a new topic.
rpk cluster config set auto_create_topics_enabled false

existing_topics="$(rpk topic list | awk 'NR > 1 { print $1 }')"

for topic in "${TOPICS[@]}"; do
  if grep -qx "${topic}" <<<"${existing_topics}"; then
    echo "topic ${topic}: already exists"
  else
    rpk topic create "${topic}" \
      --partitions "${TOPIC_PARTITIONS}" \
      --replicas 1 \
      --topic-config "retention.ms=${TOPIC_RETENTION_MS}"
  fi
done

rpk topic list
