import argparse
import concurrent.futures
import json
import logging
import os
import re
import site
from functools import partial

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

    def __init__(self, config_file):
        self.config_file = config_file
        self.config_dir = self._determine_config_dir()
        self.config_path = os.path.join(self.config_dir, config_file)
        self.config = self._load_config()

    def _determine_config_dir(self):
        if any(site_path in os.path.abspath(__file__) for site_path in site.getsitepackages()):
            return os.path.join(os.path.expanduser("~"), ".translator_po")
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def _load_config(self):
        os.makedirs(self.config_dir, exist_ok=True)
        if not os.path.exists(self.config_path):
            with open(self.config_path, 'w') as config_file:
                json.dump(self.DEFAULT_CONFIG, config_file, indent=4)
            logging.info(f"Configuration file not found. Created default config at {self.config_path}")

        with open(self.config_path, 'r') as config_file:
            return json.load(config_file)


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


class PoFileProcessor:
    def __init__(self, file_path, config, output_folder, odoo_output=False):
        self.file_path = file_path
        self.config = config
        self.output_folder = output_folder
        self.odoo_output = odoo_output
        self.file_name = os.path.basename(file_path)
        self.data = self._read_file()
        self.translator = TranslatorFactory(config).get_translator_instance()
        self.new_data = None

    def _read_file(self):
        try:
            with open(self.file_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            logging.error(f"File not found: {self.file_path}")
        except Exception as e:
            logging.error(f"Error reading file: {self.file_path}, Error: {e}")
        return None

    def _translate_entry(self, entry):
        try:
            if len(entry.msgid) > self.config.get("max_msgid_length", 300):
                return entry

            placeholders = re.findall(r'%\(\w+\)s|%\w|%%', entry.msgid)
            temp_msgid = entry.msgid
            placeholder_map = {}
            for i, placeholder in enumerate(placeholders):
                placeholder_marker = f'PLACEHOLDER_{i}'
                temp_msgid = temp_msgid.replace(placeholder, placeholder_marker)
                placeholder_map[placeholder_marker] = placeholder

            translated_text = self.translator.translate(temp_msgid)

            for placeholder_marker, placeholder in placeholder_map.items():
                translated_text = translated_text.replace(placeholder_marker, placeholder)

            entry.msgstr = translated_text
            return entry
        except Exception as e:
            logging.error(f"Translation error. The key could not be translated. Key: {entry.msgid}, Error: {e}")
            return entry

    def _translate_entries_chunk(self, entries_chunk):
        return [self._translate_entry(entry) for entry in entries_chunk]

    def translate_po_file(self):
        if self.data:
            po = polib.pofile(self.data)
            entries = po.untranslated_entries()
            num_cores = os.cpu_count()
            chunk_size = len(entries) // num_cores
            chunks = [entries[i:i + chunk_size] for i in range(0, len(entries), chunk_size)]

            with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
                worker_func = partial(self._translate_entries_chunk)
                with tqdm(total=len(chunks), desc=f"Translating {self.file_name}") as pbar:
                    results = []
                    for result in executor.map(worker_func, chunks):
                        results.append(result)
                        pbar.update()

            translated_entries = [entry for sublist in results for entry in sublist]
            po.clear()
            po.extend(translated_entries)
            update_metadata(po)
            self.new_data = str(po)

    def write_output_file(self):
        if not self.new_data:
            return

        if self.odoo_output:
            base_name = os.path.splitext(self.file_name)[0]
            output_folder_path = os.path.join(self.output_folder, base_name, 'i18n')
            output_file_name = f"{self.config['target_lang']}.po"
        else:
            output_file_name = os.path.splitext(self.file_name)[0] + f"_{self.config['target_lang']}.po"
            output_folder_path = self.output_folder

        os.makedirs(output_folder_path, exist_ok=True)
        output_file_path = os.path.join(output_folder_path, output_file_name)

        try:
            with open(output_file_path, "w") as file:
                file.write(self.new_data)
        except Exception as e:
            logging.error(f"Error writing to file: {output_file_path}, Error: {e}")

    def process(self):
        self.translate_po_file()
        self.write_output_file()


class MainController:
    def __init__(self, args):
        self.args = args
        self.config_handler = ConfigHandler(args.config_file)
        self.file_processors = []

    def process_file(self, file_path, output_folder, odoo_output):
        processor = PoFileProcessor(file_path, self.config_handler.config, output_folder, odoo_output)
        processor.process()

    def process_files_in_folder(self, folder_path, output_folder, odoo_output):
        files = [
            os.path.join(folder_path, file_name)
            for file_name in os.listdir(folder_path)
            if file_name.endswith('.po') or file_name.endswith('.pot')
        ]
        num_cores = os.cpu_count()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_cores) as executor:
            futures = [executor.submit(self.process_file, file_path, output_folder, odoo_output) for file_path in files]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error processing file: {e}")

    def run(self):
        if self.args.file_path:
            self.process_file(self.args.file_path, self.args.output_folder, self.args.odoo_output)
        elif self.args.folder_path:
            self.process_files_in_folder(self.args.folder_path, self.args.output_folder, self.args.odoo_output)
        else:
            logging.error("Either --file_path or --folder_path must be provided.")


def main():
    parser = argparse.ArgumentParser(description="Translate .po and .pot files.")
    parser.add_argument('-f', '--file_path', type=str, help='Path to the input .po or .pot file')
    parser.add_argument('-d', '--folder_path', type=str, help='Path to the folder containing .po or .pot files')
    parser.add_argument('-o', '--output_folder', type=str, help='Path to the output folder')
    parser.add_argument('-c', '--config_file', type=str, default='config.json', help='Path to the configuration file')
    parser.add_argument('-O', '--odoo_output', action='store_true', help='Enable Odoo output format')

    args = parser.parse_args()

    controller = MainController(args)
    controller.run()


def update_metadata(po):
    po.metadata['Last-Translator'] = 'Zahfron Adani Kautsar (tickernelz)'
    po.metadata['Language-Team'] = 'Zahfron Adani Kautsar (tickernelz)'


if __name__ == "__main__":
    main()