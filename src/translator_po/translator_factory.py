from deep_translator import (
    GoogleTranslator,
    PonsTranslator,
    LingueeTranslator,
    MyMemoryTranslator,
    YandexTranslator,
    MicrosoftTranslator,
    QcriTranslator,
    DeeplTranslator,
    LibreTranslator,
    PapagoTranslator,
    ChatGptTranslator,
    BaiduTranslator,
)
class TranslatorFactory:
    TRANSLATORS = {
        "GoogleTranslator": GoogleTranslator,
        "PonsTranslator": PonsTranslator,
        "LingueeTranslator": LingueeTranslator,
        "MyMemoryTranslator": MyMemoryTranslator,
        "YandexTranslator": YandexTranslator,
        "MicrosoftTranslator": MicrosoftTranslator,
        "QcriTranslator": QcriTranslator,
        "DeeplTranslator": DeeplTranslator,
        "LibreTranslator": LibreTranslator,
        "PapagoTranslator": PapagoTranslator,
        "ChatGptTranslator": ChatGptTranslator,
        "BaiduTranslator": BaiduTranslator,
    }

    def __init__(self, config):
        self.config = config

    def get_translator_instance(self):
        translator_name = self.config["translator"]
        translator_class = self.TRANSLATORS[translator_name]
        translator_params = self.config.get(translator_name, {})
        translator_params.update({"source": self.config["source_lang"], "target": self.config["target_lang"]})
        return translator_class(**translator_params)
