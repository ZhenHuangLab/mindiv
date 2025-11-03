#!/usr/bin/env python3
"""
Simple runner script for mindiv service.
"""
import sys
import uvicorn
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mindiv.config import load_config, set_config

if __name__ == "__main__":
    # Load configuration
    config_path = Path(__file__).parent / "config" / "config.yaml"
    pricing_path = Path(__file__).parent / "config" / "pricing.yaml"
    
    if config_path.exists():
        config = load_config(config_path, pricing_path)
        set_config(config)
        print(f"Loaded configuration from {config_path}")
    else:
        print(f"Warning: Config file not found at {config_path}")
        print("Using default configuration")
        from mindiv.config import Config
        config = Config()
        set_config(config)
    
    # Run server
    uvicorn.run(
        "mindiv.main:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_level=config.log_level.lower(),
    )

