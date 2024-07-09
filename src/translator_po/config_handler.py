import json
import logging
import os
import site

logger = logging.getLogger(__name__)


class ConfigHandler:
    DEFAULT_CONFIG = {
        "translator": "GoogleTranslator",
        "source_lang": "id",
        "target_lang": "en",
        "max_msgid_length": 300,
        "DeeplTranslator": {"api_key": "", "use_free_api": True},
        "QcriTranslator": {"api_key": ""},
        "YandexTranslator": {"api_key": ""},
        "MicrosoftTranslator": {"api_key": "", "region": ""},
        "LibreTranslator": {"api_key": "", "use_free_api": True, "custom_url": ""},
        "PapagoTranslator": {"client_id": "", "secret_key": ""},
        "ChatGptTranslator": {"api_key": "", "model": "gpt-3.5-turbo"},
        "BaiduTranslator": {"appid": "", "appkey": ""},
    }

    def __init__(self, config_file, cli_config_path=None):
        self.config_file = config_file
        self.cli_config_path = cli_config_path
        self.config_dir = self._determine_config_dir()
        self.config_path = os.path.join(self.config_dir, config_file)
        logger.info(f"Loading configuration from {self.config_path}")
        self.config = self._load_config()

    def _determine_config_dir(self):
        if self.cli_config_path:
            return os.path.dirname(os.path.abspath(self.cli_config_path))

        if any(site_path in os.path.abspath(__file__) for site_path in site.getsitepackages()):
            return os.path.join(os.path.expanduser("~"), ".translator_po")
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def _load_config(self):
        os.makedirs(self.config_dir, exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, 'w') as config_file:
                json.dump(self.DEFAULT_CONFIG, config_file, indent=4)
            logger.info(f"Configuration file not found. Created default config at {self.config_path}")

        with open(self.config_path, 'r') as config_file:
            config = json.load(config_file)

        logger.info(f"Using translator: {config['translator']}")
        return config
