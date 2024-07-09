import argparse
import concurrent.futures
import json
import logging
import os
import re
import signal
import site
from functools import partial

import colorlog
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
from termcolor import colored
from tqdm import tqdm

# Set up signal handling
shutdown_flag = False
translation_error_flag = False


def signal_handler(signum, frame):
    global shutdown_flag
    shutdown_flag = True
    logger.info("Received shutdown signal, terminating forcefully...")
    os._exit(1)  # Forcefully exit the program


# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Setup colorlog
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        '%(asctime)s - %(log_color)s%(levelname)s%(reset)s - Process %(process)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        },
    )
)

# Check if the root logger already has handlers configured
logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Root logger configuration
if not logger.hasHandlers():
    # Configure logging to include timestamps and process id
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


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
    def __init__(self, file_path, config, output_folder, odoo_output=False, jobs=max(1, os.cpu_count()), force=False):
        self.file_path = file_path
        self.config = config
        self.output_folder = output_folder
        self.odoo_output = odoo_output
        self.jobs = jobs
        self.force = force
        self.file_name = os.path.basename(file_path)
        self.data = self._read_file()
        self.translator = TranslatorFactory(config).get_translator_instance()
        self.new_data = None

    def _read_file(self):
        try:
            with open(self.file_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            logger.error(f"File not found: {self.file_path}")
        except Exception as e:
            logger.error(f"Error reading file: {self.file_path}, Error: {e}")
        return None

    def _translate_entry(self, entry):
        global translation_error_flag

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
            translation_error_flag = True
            logger.error(f"{self.file_name}: {e}")
            raise

    def _translate_entries_chunk(self, entries_chunk):
        global shutdown_flag, translation_error_flag

        if shutdown_flag or translation_error_flag:
            logger.info("Shutting down translation due to interrupt signal or translation error.")
            return []

        translated_entries = []
        for entry in entries_chunk:
            if translation_error_flag:
                break

            translated_entries.append(self._translate_entry(entry))

        return translated_entries

    def translate_po_file(self):
        global shutdown_flag, translation_error_flag
        if self.data:
            po = polib.pofile(self.data)
            entries = po.untranslated_entries()
            chunk_size = max(1, len(entries) // self.jobs)
            chunks = [entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)]

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.jobs) as executor:
                worker_func = partial(self._translate_entries_chunk)
                results = []
                with tqdm(total=len(entries), desc=colored(f"Translating {self.file_name}", 'green')) as pbar:
                    future_to_chunk = {executor.submit(worker_func, chunk): chunk for chunk in chunks}
                    for future in concurrent.futures.as_completed(future_to_chunk):
                        if shutdown_flag or translation_error_flag:
                            logger.info("Gracefully stopping execution.")
                            executor.shutdown(wait=False, cancel_futures=True)
                            break

                        try:
                            result = future.result()
                            results.append(result)
                            pbar.update(len(future_to_chunk[future]))
                        except Exception as e:
                            logger.error(f"Translation error for file {self.file_name}: {e}")
                            translation_error_flag = True
                            executor.shutdown(wait=False, cancel_futures=True)
                            break

            if not shutdown_flag and not translation_error_flag:
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
            logger.error(f"Error writing to file: {output_file_path}, Error: {e}")

    def process(self):
        if self.odoo_output:
            base_name = os.path.splitext(self.file_name)[0]
            output_folder_path = os.path.join(self.output_folder, base_name, 'i18n')
            output_file_name = f"{self.config['target_lang']}.po"
        else:
            output_file_name = os.path.splitext(self.file_name)[0] + f"_{self.config['target_lang']}.po"
            output_folder_path = self.output_folder

        output_file_path = os.path.join(output_folder_path, output_file_name)

        if not self.force and os.path.exists(output_file_path):
            logger.info(f"File {output_file_path} already exists. Skipping translation.")
            return

        self.translate_po_file()
        self.write_output_file()


class PoFileSplitter:
    def __init__(self, file_path, num_split, output_folder):
        self.file_path = file_path
        self.num_split = num_split
        self.output_folder = output_folder
        self.file_name = os.path.basename(file_path)
        self.data = self._read_file()

    def _read_file(self):
        try:
            with open(self.file_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            logger.error(f"File not found: {self.file_path}")
        except Exception as e:
            logger.error(f"Error reading file: {self.file_path}, Error: {e}")
        return None

    def split_po_file(self):
        if self.data:
            po = polib.pofile(self.data)
            entries = po.untranslated_entries()
            chunk_size = max(1, len(entries) // self.num_split)
            chunks = [entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)]

            for i, chunk in enumerate(chunks):
                split_po = polib.POFile()
                split_po.extend(chunk)
                output_file_name = os.path.splitext(self.file_name)[0] + f"_part_{i + 1}.po"
                output_file_path = os.path.join(self.output_folder, output_file_name)
                os.makedirs(self.output_folder, exist_ok=True)
                split_po.save(output_file_path)
                logger.info(f"Saved split file: {output_file_path}")


class PoFileMerger:
    def __init__(self, folder_path, output_file):
        self.folder_path = folder_path
        self.output_file = output_file

    def merge_po_files(self):
        merged_po = polib.POFile()
        for file_name in os.listdir(self.folder_path):
            if file_name.endswith('.po'):
                file_path = os.path.join(self.folder_path, file_name)
                po = polib.pofile(file_path)
                merged_po.extend(po)
        merged_po.save(self.output_file)
        logger.info(f"Merged file saved: {self.output_file}")


class MainController:
    def __init__(self, args):
        self.args = args
        cli_config_path = args.config_file if args.config_file else None
        self.config_handler = ConfigHandler(args.config_file, cli_config_path)
        self.jobs = args.jobs
        self.force = args.force
        self.file_processors = []

    def process_file(self, file_path, output_folder, odoo_output):
        processor = PoFileProcessor(
            file_path, self.config_handler.config, output_folder, odoo_output, self.jobs, self.force
        )
        processor.process()

    def process_files_in_folder(self, folder_path, output_folder, odoo_output):
        global shutdown_flag, translation_error_flag
        files = [
            os.path.join(folder_path, file_name)
            for file_name in os.listdir(folder_path)
            if file_name.endswith('.po') or file_name.endswith('.pot')
        ]

        for file_path in files:
            if shutdown_flag or translation_error_flag:
                logger.info("Gracefully stopping file processing due to interrupt signal or translation error.")
                break

            try:
                self.process_file(file_path, output_folder, odoo_output)
            except Exception as e:
                logger.error(f"Error processing file: {e}")

    def run(self):
        if self.args.split:
            if not self.args.num_split or not self.args.output_split:
                logger.error("Parameters --num_split and --output_split are required for splitting.")
                return
            logger.info(f"Splitting file: {self.args.split} into {self.args.num_split} parts")
            splitter = PoFileSplitter(self.args.split, self.args.num_split, self.args.output_split)
            splitter.split_po_file()
        elif self.args.merge:
            if not self.args.output_merge:
                logger.error("Parameter --output_merge is required for merging.")
                return
            logger.info(f"Merging files in folder: {self.args.merge} into {self.args.output_merge}")
            merger = PoFileMerger(self.args.merge, self.args.output_merge)
            merger.merge_po_files()
        elif self.args.file_path:
            logger.info(f"Single file mode. Processing file: {self.args.file_path}")
            self.process_file(self.args.file_path, self.args.output_folder, self.args.odoo_output)
        elif self.args.folder_path:
            logger.info(f"Folder mode. Processing files in folder: {self.args.folder_path}")
            self.process_files_in_folder(self.args.folder_path, self.args.output_folder, self.args.odoo_output)
        else:
            logger.error("Either --file_path, --folder_path, --split, or --merge must be provided.")


def main():
    parser = argparse.ArgumentParser(description="Translate .po and .pot files.")
    parser.add_argument('-f', '--file_path', type=str, help='Path to the input .po or .pot file')
    parser.add_argument('-d', '--folder_path', type=str, help='Path to the folder containing .po or .pot files')
    parser.add_argument('-o', '--output_folder', type=str, help='Path to the output folder')
    parser.add_argument('-c', '--config_file', type=str, default='config.json', help='Path to the configuration file')
    parser.add_argument('-O', '--odoo_output', action='store_true', help='Enable Odoo output format')
    parser.add_argument('-j', '--jobs', type=int, default=os.cpu_count(), help='Number of concurrent jobs/threads')
    parser.add_argument('-s', '--split', type=str, help='Path to the input .po file to split')
    parser.add_argument('-ns', '--num_split', type=int, help='Number of parts to split the .po file into')
    parser.add_argument('-os', '--output_split', type=str, help='Path to the output folder for split files')
    parser.add_argument('-m', '--merge', type=str, help='Path to the folder containing .po files to merge')
    parser.add_argument('-om', '--output_merge', type=str, help='Path to the output merged .po file')
    parser.add_argument(
        '-F', '--force', action='store_true', help='Force processing even if output file already exists'
    )

    args = parser.parse_args()

    controller = MainController(args)
    controller.run()


def update_metadata(po):
    po.metadata['Last-Translator'] = 'Zahfron Adani Kautsar (tickernelz)'
    po.metadata['Language-Team'] = 'Zahfron Adani Kautsar (tickernelz)'


if __name__ == "__main__":
    main()
