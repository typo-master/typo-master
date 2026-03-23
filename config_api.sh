#!/bin/bash
# Configure OpenAI-compatible API for Alibaba Cloud Bailian

export OPENAI_API_KEY="sk-sp-6ae28092e0874696a091f765c7e0118b"
export OPENAI_BASE_URL="https://coding.dashscope.aliyuncs.com/apps/anthropic"
export OPENAI_MODEL="kimi-k2.5"
export LLM_ENABLED="true"

echo "API configured:"
echo "  Base URL: $OPENAI_BASE_URL"
echo "  Model: $OPENAI_MODEL"
echo "  API Key: ${OPENAI_API_KEY:0:10}..."
