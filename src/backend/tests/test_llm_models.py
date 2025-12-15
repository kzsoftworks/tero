import pytest
from unittest.mock import patch

from .common import *

from tero.ai_models.ai_factory import providers
from tero.ai_models.aws_provider import AWSProvider
from tero.ai_models.domain import LlmModel, LlmModelType, LlmModelVendor
from tero.ai_models.google_provider import GoogleProvider


@pytest.fixture(name="ai_models")
def ai_models_fixture() -> List[LlmModel]:
    return [
        LlmModel(id="gpt-5-nano", model_type=LlmModelType.REASONING, name="GPT-5 Nano", description="This is a new reasoning model that will replace GPT-4.1 Nano in the short term.",
                 token_limit=4000000, output_token_limit=128000, prompt_1k_token_usd=0.00005, completion_1k_token_usd=0.0004, model_vendor=LlmModelVendor.OPENAI),
        LlmModel(id="gpt-5-mini", model_type=LlmModelType.REASONING, name="GPT-5 Mini", description="This is a new reasoning model that will replace GPT-4o Mini in the short term. It has a good balance between cost and intelligence.",
                 token_limit=400000, output_token_limit=128000, prompt_1k_token_usd=0.00025, completion_1k_token_usd=0.002, model_vendor=LlmModelVendor.OPENAI),
        LlmModel(id="gemini-2.5-flash", model_type=LlmModelType.CHAT, name="Gemini 2.5 Flash", description="This is a fast and efficient model, comparable to GPT-4.1 Nano, optimized for speed while maintaining high quality responses.",
                 token_limit=1048576, output_token_limit=65536, prompt_1k_token_usd=0.0003, completion_1k_token_usd=0.0025, model_vendor=LlmModelVendor.GOOGLE),
        LlmModel(id="o4-mini", model_type=LlmModelType.REASONING, name="O4 Mini", description="This is a reasoning model that is good for coding, math and some complex tasks.",
                 token_limit=200000, output_token_limit=100000, prompt_1k_token_usd=0.0011, completion_1k_token_usd=0.0044, model_vendor=LlmModelVendor.OPENAI),
        LlmModel(id="gemini-2.5-pro", model_type=LlmModelType.CHAT, name="Gemini 2.5 Pro", description="This is an advanced reasoning model, outperforming GPT-4o with a larger context while being more affordable.",
                 token_limit=1048576, output_token_limit=65536, prompt_1k_token_usd=0.00125, completion_1k_token_usd=0.01, model_vendor=LlmModelVendor.GOOGLE),
        LlmModel(id="gpt-4o-mini", model_type=LlmModelType.CHAT, name="GPT-4o Mini", description="This is the best model for simple tasks",
                 token_limit=64000, output_token_limit=2048, prompt_1k_token_usd=0.0025, completion_1k_token_usd=0.0075, model_vendor=LlmModelVendor.OPENAI),
        LlmModel(id="claude-sonnet-4", model_type=LlmModelType.CHAT, name="Claude Sonnet 4", description="This is a similar model to GPT-4o but with better reasoning.",
                 token_limit=200000, output_token_limit=64000, prompt_1k_token_usd=0.003, completion_1k_token_usd=0.015, model_vendor=LlmModelVendor.ANTHROPIC),
        LlmModel(id="gpt-4o", model_type=LlmModelType.CHAT, name="GPT-4o", description="This is the best model for complex tasks", token_limit=128000,
                 output_token_limit=4096, prompt_1k_token_usd=0.005, completion_1k_token_usd=0.015, model_vendor=LlmModelVendor.OPENAI)
    ]

async def test_find_models(client: AsyncClient, ai_models: List[LlmModel]):
    resp = await client.get(f"{BASE_PATH}/models")
    assert_response(resp, ai_models)


@patch("tero.ai_models.ai_factory.providers", [p for p in providers if not isinstance(p, AWSProvider)])
async def test_claude_sonnet_4_not_available(client: AsyncClient, ai_models: List[LlmModel]):
    resp = await client.get(f"{BASE_PATH}/models")
    assert_response(resp, [model for model in ai_models if model.id != "claude-sonnet-4"])


@patch("tero.ai_models.ai_factory.providers", [p for p in providers if not isinstance(p, GoogleProvider)])
async def test_gemini_2_5_pro_not_available(client: AsyncClient, ai_models: List[LlmModel]):
    resp = await client.get(f"{BASE_PATH}/models")
    assert_response(resp, [model for model in ai_models if model.id not in ["gemini-2.5-flash", "gemini-2.5-pro"]])
