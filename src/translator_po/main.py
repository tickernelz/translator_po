import argparse
import json
import logging
import multiprocessing
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


def update_metadata(po):
    po.metadata['Last-Translator'] = 'Zahfron Adani Kautsar (tickernelz)'
    po.metadata['Language-Team'] = 'Zahfron Adani Kautsar (tickernelz)'


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
                return entry

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

            entry.msgstr = translated_text
            return entry
        except Exception as e:
            logging.error(f"Translation error. The key could not be translated. Key: {entry.msgid}, Error: {e}")
            return entry

    def translate_entries_chunk(self, entries_chunk):
        return [self.translate_entry(entry) for entry in entries_chunk]

    def translate_po_file(self):
        if self.data:
            po = polib.pofile(self.data)
            entries = po.untranslated_entries()

            # Determine the number of available CPU cores
            num_cores = multiprocessing.cpu_count()

            # Split entries into chunks
            chunk_size = len(entries) // num_cores
            chunks = [entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)]

            # Create a pool of workers
            with multiprocessing.Pool(processes=num_cores) as pool:
                # Use partial to pass the self parameter to the worker function
                worker_func = partial(self.translate_entries_chunk)

                # Initialize tqdm progress bar
                with tqdm(total=len(chunks), desc=f"Translating {self.file_name}") as pbar:
                    results = []
                    for result in pool.imap(worker_func, chunks):
                        results.append(result)
                        pbar.update()

            # Flatten the list of results
            translated_entries = [entry for sublist in results for entry in sublist]

            # Update the po object with translated entries
            po.clear()
            po.extend(translated_entries)

            update_metadata(po)
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
    except Exception as e:
        logging.error(f"Error writing to file: {output_file_path}, Error: {e}")


def worker(task, queue):
    while True:
        args = queue.get()
        if args is None:
            queue.task_done()
            break
        task(*args)
        queue.task_done()


def process_files_in_folder(folder_path, output_folder, config, odoo_output):
    files = [
        os.path.join(folder_path, file_name)
        for file_name in os.listdir(folder_path)
        if file_name.endswith('.po') or file_name.endswith('.pot')
    ]
    nprocesses = multiprocessing.cpu_count()
    queue = multiprocessing.JoinableQueue()

    for i in range(nprocesses):
        p = multiprocessing.Process(target=worker, args=(process_file, queue))
        p.start()

    for file_path in files:
        queue.put((file_path, output_folder, config, odoo_output))

    for i in range(nprocesses):
        queue.put(None)

    queue.join()


def main():
    parser = argparse.ArgumentParser(description="Translate .po and .pot files.")
    parser.add_argument('-f', '--file_path', type=str, help='Path to the input .po or .pot file')
    parser.add_argument('-d', '--folder_path', type=str, help='Path to the folder containing .po or .pot files')
    parser.add_argument('-o', '--output_folder', type=str, help='Path to the output folder')
    parser.add_argument('-c', '--config_file', type=str, default='config.json', help='Path to the configuration file')
    parser.add_argument('-O', '--odoo_output', action='store_true', help='Enable Odoo output format')

    args = parser.parse_args()

    # Determine the configuration file path
    if any(site_path in os.path.abspath(__file__) for site_path in site.getsitepackages()):
        # The program is installed as a module
        config_dir = os.path.join(os.path.expanduser("~"), ".translator_po")
    else:
        # The program is not installed as a module
        config_dir = os.path.dirname(os.path.abspath(__file__))

    os.makedirs(config_dir, exist_ok=True)
    config_file_path = os.path.join(config_dir, args.config_file)

    # Check if the configuration file exists, if not create it with default settings
    if not os.path.exists(config_file_path):
        with open(config_file_path, 'w') as config_file:
            json.dump(DEFAULT_CONFIG, config_file, indent=4)
        logging.info(f"Configuration file not found. Created default config at {config_file_path}")

    # Load configuration
    with open(config_file_path, 'r') as config_file:
        config = json.load(config_file)

    if args.file_path:
        process_file(args.file_path, args.output_folder, config, args.odoo_output)
    elif args.folder_path:
        process_files_in_folder(args.folder_path, args.output_folder, config, args.odoo_output)
        logging.info("Translation complete.")
    else:
        logging.error("Either --file_path or --folder_path must be provided.")


if __name__ == "__main__":
    multiprocessing.set_start_method('fork', force=True)
    main()
