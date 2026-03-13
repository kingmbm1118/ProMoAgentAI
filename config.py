"""
Configuration Module for ProMoAgentAI
Supports multiple LLM providers and external services
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Application configuration with support for:
    - Multiple LLM providers (OpenAI, Anthropic, Google)
    - Camunda BPM deployment
    - External BPMN viewer (demo.bpmn.io)
    - Batch processing settings
    """

    # API Keys for different LLM providers
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Model selection - defaults to sonnet-4.5 as per paper
    # Options: "sonnet-4.5", "gpt-5.2", "gemini-3"
    MODEL_NAME = os.getenv("MODEL_NAME", "sonnet-4.5")

    # Camunda configuration
    CAMUNDA_URL = os.getenv("CAMUNDA_URL", "http://localhost:8080")
    CAMUNDA_USERNAME = os.getenv("CAMUNDA_USERNAME", "demo")
    CAMUNDA_PASSWORD = os.getenv("CAMUNDA_PASSWORD", "demo")

    # External BPMN Viewer
    BPMN_IO_VIEWER_URL = os.getenv("BPMN_IO_VIEWER_URL", "https://demo.bpmn.io")

    # Batch Processing Settings
    BATCH_OUTPUT_DIR = os.getenv("BATCH_OUTPUT_DIR", "./batch_output")
    BATCH_MAX_CONCURRENT = int(os.getenv("BATCH_MAX_CONCURRENT", "1"))

    # Generation Settings
    MAX_FIX_ITERATIONS = int(os.getenv("MAX_FIX_ITERATIONS", "5"))
    MAX_CAMUNDA_ATTEMPTS = int(os.getenv("MAX_CAMUNDA_ATTEMPTS", "3"))
    GENERATION_TIMEOUT = int(os.getenv("GENERATION_TIMEOUT", "180"))  # seconds

    # Model configurations as per paper's Table 2
    MODEL_CONFIGS = {
        "sonnet-4.5": {
            "provider": "anthropic",
            "model_id": "claude-sonnet-4-5-20250929",
            "api_key_env": "ANTHROPIC_API_KEY",
            "display_name": "Claude Sonnet 4.5",
            "description": "Best balance of quality and speed",
            "paper_score": 0.95
        },
        "gpt-5.2": {
            "provider": "openai",
            "model_id": "gpt-4o",  # Using GPT-4o as GPT-5.2 placeholder
            "api_key_env": "OPENAI_API_KEY",
            "display_name": "GPT-5.2",
            "description": "Strong reasoning capabilities",
            "paper_score": 0.94
        },
        "gemini-3": {
            "provider": "google",
            "model_id": "gemini-1.5-pro",  # Using Gemini 1.5 Pro as Gemini 3 placeholder
            "api_key_env": "GOOGLE_API_KEY",
            "display_name": "Gemini 3",
            "description": "Fast processing with good quality",
            "paper_score": 0.97
        }
    }

    # Feature flags
    ENABLE_CAMUNDA_DEPLOYMENT = os.getenv("ENABLE_CAMUNDA_DEPLOYMENT", "true").lower() == "true"
    ENABLE_BATCH_PROCESSING = os.getenv("ENABLE_BATCH_PROCESSING", "true").lower() == "true"
    ENABLE_EXTERNAL_VIEWER = os.getenv("ENABLE_EXTERNAL_VIEWER", "true").lower() == "true"
    ENABLE_ARABIC_SUPPORT = os.getenv("ENABLE_ARABIC_SUPPORT", "true").lower() == "true"

    @classmethod
    def get_current_model_config(cls):
        """Get configuration for currently selected model"""
        if cls.MODEL_NAME not in cls.MODEL_CONFIGS:
            raise ValueError(
                f"Invalid MODEL_NAME: {cls.MODEL_NAME}. "
                f"Must be one of: {list(cls.MODEL_CONFIGS.keys())}"
            )
        return cls.MODEL_CONFIGS[cls.MODEL_NAME]

    @classmethod
    def validate(cls):
        """Validate that required API key is present for selected model"""
        model_config = cls.get_current_model_config()
        api_key_env = model_config["api_key_env"]

        if api_key_env == "OPENAI_API_KEY" and not cls.OPENAI_API_KEY:
            raise ValueError(f"OPENAI_API_KEY required for model {cls.MODEL_NAME}")
        elif api_key_env == "ANTHROPIC_API_KEY" and not cls.ANTHROPIC_API_KEY:
            raise ValueError(f"ANTHROPIC_API_KEY required for model {cls.MODEL_NAME}")
        elif api_key_env == "GOOGLE_API_KEY" and not cls.GOOGLE_API_KEY:
            raise ValueError(f"GOOGLE_API_KEY required for model {cls.MODEL_NAME}")

        return True

    @classmethod
    def get_api_key_for_model(cls):
        """Get the appropriate API key for the selected model"""
        model_config = cls.get_current_model_config()
        api_key_env = model_config["api_key_env"]

        if api_key_env == "OPENAI_API_KEY":
            return cls.OPENAI_API_KEY
        elif api_key_env == "ANTHROPIC_API_KEY":
            return cls.ANTHROPIC_API_KEY
        elif api_key_env == "GOOGLE_API_KEY":
            return cls.GOOGLE_API_KEY

        return None

    @classmethod
    def get_all_available_models(cls):
        """Get list of models that have API keys configured"""
        available = []

        for model_name, config in cls.MODEL_CONFIGS.items():
            api_key_env = config["api_key_env"]

            has_key = False
            if api_key_env == "OPENAI_API_KEY" and cls.OPENAI_API_KEY:
                has_key = True
            elif api_key_env == "ANTHROPIC_API_KEY" and cls.ANTHROPIC_API_KEY:
                has_key = True
            elif api_key_env == "GOOGLE_API_KEY" and cls.GOOGLE_API_KEY:
                has_key = True

            if has_key:
                available.append({
                    "name": model_name,
                    **config
                })

        return available

    @classmethod
    def get_viewer_url(cls, bpmn_content: str = None) -> str:
        """Get the external viewer URL"""
        base_url = cls.BPMN_IO_VIEWER_URL

        if bpmn_content:
            import base64
            encoded = base64.b64encode(bpmn_content.encode()).decode()
            return f"{base_url}/new#source=data:application/bpmn+xml;base64,{encoded}"

        return base_url

    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("=" * 50)
        print("ProMoAgentAI Configuration")
        print("=" * 50)
        print(f"Model: {cls.MODEL_NAME}")

        model_config = cls.get_current_model_config()
        print(f"Provider: {model_config['provider']}")
        print(f"Model ID: {model_config['model_id']}")

        print(f"\nCamunda URL: {cls.CAMUNDA_URL}")
        print(f"Camunda Deployment: {'Enabled' if cls.ENABLE_CAMUNDA_DEPLOYMENT else 'Disabled'}")

        print(f"\nExternal Viewer: {'Enabled' if cls.ENABLE_EXTERNAL_VIEWER else 'Disabled'}")
        print(f"Batch Processing: {'Enabled' if cls.ENABLE_BATCH_PROCESSING else 'Disabled'}")
        print(f"Arabic Support: {'Enabled' if cls.ENABLE_ARABIC_SUPPORT else 'Disabled'}")

        print(f"\nMax Fix Iterations: {cls.MAX_FIX_ITERATIONS}")
        print(f"Max Camunda Attempts: {cls.MAX_CAMUNDA_ATTEMPTS}")
        print(f"Generation Timeout: {cls.GENERATION_TIMEOUT}s")
        print("=" * 50)
