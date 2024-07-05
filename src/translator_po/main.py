import argparse
import concurrent.futures
import logging
import os
import re
import json

import polib
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
from tqdm import tqdm

# Configure logging to include timestamps
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Map of translator names to their corresponding classes
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


class PoFileTranslator:
    def __init__(self, data, config, file_name):
        self.data = data
        self.config = config
        self.file_name = file_name
        self.translator_class = TRANSLATORS[config["translator"]]
        self.source_lang = config["source_lang"]
        self.target_lang = config["target_lang"]
        self.max_msgid_length = config.get("max_msgid_length", 300)
        self.translator_instance = self.create_translator_instance()
        self.new_data = self.translate_po_file()

    def create_translator_instance(self):
        translator_name = self.config["translator"]
        translator_params = {
            "DeeplTranslator": {
                "source": self.source_lang,
                "target": self.target_lang,
                "api_key": self.config["DeeplTranslator"]["api_key"],
                "use_free_api": self.config["DeeplTranslator"]["use_free_api"],
            },
            "QcriTranslator": {
                "source": self.source_lang,
                "target": self.target_lang,
                "api_key": self.config["QcriTranslator"]["api_key"],
            },
            "YandexTranslator": {
                "source": self.source_lang,
                "target": self.target_lang,
                "api_key": self.config["YandexTranslator"]["api_key"],
            },
            "MicrosoftTranslator": {
                "source": self.source_lang,
                "target": self.target_lang,
                "api_key": self.config["MicrosoftTranslator"]["api_key"],
                "region": self.config["MicrosoftTranslator"]["region"],
            },
            "LibreTranslator": {
                "source": self.source_lang,
                "target": self.target_lang,
                "api_key": self.config["LibreTranslator"]["api_key"],
                "use_free_api": self.config["LibreTranslator"]["use_free_api"],
                "custom_url": self.config["LibreTranslator"]["custom_url"],
            },
            "PapagoTranslator": {
                "source": self.source_lang,
                "target": self.target_lang,
                "client_id": self.config["PapagoTranslator"]["client_id"],
                "secret_key": self.config["PapagoTranslator"]["secret_key"],
            },
            "ChatGptTranslator": {
                "source": self.source_lang,
                "target": self.target_lang,
                "api_key": self.config["ChatGptTranslator"]["api_key"],
                "model": self.config["ChatGptTranslator"]["model"],
            },
            "BaiduTranslator": {
                "source": self.source_lang,
                "target": self.target_lang,
                "appid": self.config["BaiduTranslator"]["appid"],
                "appkey": self.config["BaiduTranslator"]["appkey"],
            },
        }

        params = translator_params.get(translator_name, {"source": self.source_lang, "target": self.target_lang})
        return self.translator_class(**params)

    def translate_entry(self, entry):
        try:
            if len(entry.msgid) > self.max_msgid_length:
                return entry, None

            # Find all placeholders
            placeholders = re.findall(r'%\(\w+\)s|%\w|%%', entry.msgid)

            # Replace placeholders with temporary markers
            temp_msgid = entry.msgid
            placeholder_map = {}
            for i, placeholder in enumerate(placeholders):
                placeholder_marker = f'PLACEHOLDER_{i}'
                temp_msgid = temp_msgid.replace(placeholder, placeholder_marker)
                placeholder_map[placeholder_marker] = placeholder

            # Translate the text without placeholders
            translated_text = self.translator_instance.translate(temp_msgid)

            # Restore placeholders in the translated text
            for placeholder_marker, placeholder in placeholder_map.items():
                translated_text = translated_text.replace(placeholder_marker, placeholder)

            return entry, translated_text
        except Exception as e:
            logging.error(f"Translation error. The key could not be translated. Key: {entry.msgid}, Error: {e}")
            return entry, None

    def update_metadata(self, po):
        po.metadata['Last-Translator'] = 'Zahfron Adani Kautsar alias tickernelz'
        po.metadata['Language-Team'] = 'Zahfron Adani Kautsar alias tickernelz'

    def translate_po_file(self):
        if self.data:
            po = polib.pofile(self.data)
            total_entries = len(po)
            logging.info(f"Translating file: {self.file_name} with {total_entries} entries.")

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.translate_entry, entry) for entry in po if entry.msgid]
                for future in tqdm(
                    concurrent.futures.as_completed(futures),
                    total=total_entries,
                    ncols=100,
                    desc=f"Translating {self.file_name}",
                ):
                    entry, translation = future.result()
                    if translation is not None:
                        entry.msgstr = translation

            self.update_metadata(po)
            return str(po)


def process_file(file_path, output_folder, config, odoo_output=False):
    try:
        with open(file_path, 'r') as file:
            data = file.read()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return
    except Exception as e:
        logging.error(f"Error reading file: {file_path}, Error: {e}")
        return

    file_name = os.path.basename(file_path)
    translator = PoFileTranslator(data, config, file_name)

    if odoo_output:
        base_name = os.path.splitext(file_name)[0]
        output_folder_path = os.path.join(output_folder, base_name, 'i18n')
        os.makedirs(output_folder_path, exist_ok=True)
        output_file_name = f"{config['target_lang']}.po"
    else:
        output_file_name = os.path.splitext(file_name)[0] + f"_{config['target_lang']}.po"
        output_folder_path = output_folder

    output_file_path = os.path.join(output_folder_path, output_file_name)

    try:
        with open(output_file_path, "w") as file:
            file.write(translator.new_data)
        logging.info(f"Translation completed successfully. Output file: {output_file_path}")
    except Exception as e:
        logging.error(f"Error writing to file: {output_file_path}, Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Translate .po and .pot files.")
    parser.add_argument('--file_path', type=str, help='Path to the input .po or .pot file')
    parser.add_argument('--folder_path', type=str, help='Path to the folder containing .po or .pot files')
    parser.add_argument('output_folder', type=str, help='Path to the output folder')
    parser.add_argument('config_file', type=str, default='config.json', help='Path to the configuration file')
    parser.add_argument('--odoo_output', action='store_true', help='Enable Odoo output format')

    args = parser.parse_args()

    # Check if the configuration file exists, if not create it with default settings
    if not os.path.exists(args.config_file):
        with open(args.config_file, 'w') as config_file:
            json.dump(DEFAULT_CONFIG, config_file, indent=4)
        logging.info(f"Configuration file not found. Created default config at {args.config_file}")

    # Load configuration
    with open(args.config_file, 'r') as config_file:
        config = json.load(config_file)

    if args.file_path:
        process_file(args.file_path, args.output_folder, config, args.odoo_output)
    elif args.folder_path:
        for file_name in os.listdir(args.folder_path):
            if file_name.endswith('.po') or file_name.endswith('.pot'):
                file_path = os.path.join(args.folder_path, file_name)
                process_file(file_path, args.output_folder, config, args.odoo_output)
    else:
        logging.error("Either --file_path or --folder_path must be provided.")


if __name__ == "__main__":
    main()
