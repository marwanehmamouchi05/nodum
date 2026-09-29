"""Lazy Bedrock Converse adapter using the AWS SDK credential provider chain."""
from dataclasses import dataclass
import os
from typing import Protocol


class BedrockUnavailable(Exception):
    pass


class ConverseGateway(Protocol):
    def converse(self, *, messages: list[dict], system: list[dict],
                 tool_config: dict) -> dict: ...


@dataclass(frozen=True)
class BedrockSettings:
    region: str = "eu-north-1"
    model_id: str = "eu.amazon.nova-2-lite-v1:0"
    enabled: bool = True
    max_tokens: int = 1000
    max_rounds: int = 5
    max_tool_calls: int = 12

    @classmethod
    def from_env(cls):
        enabled = os.getenv("NODUM_AI_ENABLED", "true").lower()
        if enabled not in {"true", "false"}:
            raise BedrockUnavailable("Invalid AI configuration")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or cls.region
        model = os.getenv("BEDROCK_MODEL_ID") or cls.model_id
        if not region.strip() or not model.strip():
            raise BedrockUnavailable("Invalid AI configuration")
        return cls(region=region, model_id=model, enabled=enabled == "true")


class BedrockGateway:
    def __init__(self, settings: BedrockSettings):
        self.settings = settings
        self._client = None

    def converse(self, *, messages: list[dict], system: list[dict],
                 tool_config: dict) -> dict:
        if not self.settings.enabled:
            raise BedrockUnavailable("AI is disabled")
        try:
            # No AWS SDK import, client, credential lookup, or network at app import.
            if self._client is None:
                import boto3
                from botocore.config import Config

                self._client = boto3.client(
                    "bedrock-runtime", region_name=self.settings.region,
                    config=Config(connect_timeout=3, read_timeout=25,
                                  retries={"mode": "standard", "total_max_attempts": 2}),
                )
            return self._client.converse(
                modelId=self.settings.model_id, messages=messages, system=system,
                toolConfig=tool_config,
                inferenceConfig={"maxTokens": self.settings.max_tokens, "temperature": 0},
            )
        except Exception as exc:
            # Provider errors can contain account/request details. Do not expose them.
            raise BedrockUnavailable("Bedrock is unavailable") from exc
