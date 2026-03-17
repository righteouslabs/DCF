"""
Configuration manager for the DCF calculation engine.

Loads DCF engine parameters (discount rates, tax rates, growth defaults, etc.)
from YAML config files, with fallback to hardcoded defaults.

This is separate from industry/sector parameters (handled by industry_config.py).
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DCFConfig:
    """DCF engine configuration with sensible defaults."""

    default_discount_rate = 0.10
    working_capital_decay_rate = 0.7
    risk_free_rate = 0.04
    market_premium = 0.06
    default_earnings_growth_rate = 0.05
    default_capex_growth_rate = 0.045
    terminal_value_method = "gordon_growth"
    max_terminal_growth_rate = 0.04
    min_terminal_growth_rate = 0.02
    tax_rate_floor = 0.15
    tax_rate_ceiling = 0.35
    beta_defaults = {"default": 1.0}


class ForecastingConfig:
    """Wrapper to match expected config.forecasting.dcf access pattern."""

    def __init__(self, dcf_config):
        self.dcf = dcf_config


class Config:
    """Top-level config object."""

    def __init__(self, forecasting):
        self.forecasting = forecasting


def _load_yaml_config(config_path: str) -> dict:
    """Load config from a YAML file."""
    try:
        import yaml
    except ImportError:
        logger.debug("PyYAML not installed, skipping YAML config loading")
        return {}

    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        logger.info(f"Loaded DCF engine config from {config_path}")
        return data
    except Exception as e:
        logger.warning(f"Failed to load config from {config_path}: {e}")
        return {}


def get_config() -> Config:
    """
    Load DCF engine configuration.

    Resolution order:
    1. YAML file at DCF_ENGINE_CONFIG_PATH env var
    2. dcf_engine.yaml in the DCF module directory
    3. Hardcoded defaults

    Returns:
        Config object with config.forecasting.dcf access pattern
    """
    dcf_config = DCFConfig()

    # Try loading from YAML
    config_path = os.environ.get("DCF_ENGINE_CONFIG_PATH")
    if not config_path:
        # Default: look for dcf_engine.yaml alongside this file
        config_path = str(Path(__file__).parent / "dcf_engine.yaml")

    yaml_data = _load_yaml_config(config_path)

    # Apply YAML overrides to defaults
    dcf_section = yaml_data.get("dcf", yaml_data)
    for key, value in dcf_section.items():
        if hasattr(dcf_config, key):
            setattr(dcf_config, key, value)

    return Config(ForecastingConfig(dcf_config))
