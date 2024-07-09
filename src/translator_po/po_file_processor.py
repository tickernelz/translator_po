import concurrent.futures
import logging
import os
import re
from functools import partial

import polib
from termcolor import colored
from tqdm import tqdm

from .cache_handler import CacheHandler
from .translator_factory import TranslatorFactory
from .utils import update_metadata

logger = logging.getLogger(__name__)

# Define global flags
shutdown_flag = False
translation_error_flag = False


class PoFileProcessor:
    def __init__(
        self,
        file_path,
        config,
        output_folder,
        odoo_output=False,
        jobs=max(1, os.cpu_count()),
        force=False,
        no_cache=False,
    ):
        self.file_path = file_path
        self.config = config
        self.output_folder = output_folder
        self.odoo_output = odoo_output
        self.jobs = jobs
        self.force = force
        self.no_cache = no_cache
        self.file_name = os.path.basename(file_path)
        self.data = self._read_file()
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

    def _translate_entry(self, entry, translator, cache_handler):
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

            if cache_handler:
                cached_translation = cache_handler.get_translation(
                    self.config["source_lang"], self.config["target_lang"], self.config["translator"], temp_msgid
                )
                if cached_translation:
                    translated_text = cached_translation
                else:
                    translated_text = translator.translate(temp_msgid)
                    cache_handler.save_translation(
                        self.config["source_lang"],
                        self.config["target_lang"],
                        self.config["translator"],
                        temp_msgid,
                        translated_text,
                    )
            else:
                translated_text = translator.translate(temp_msgid)

            for placeholder_marker, placeholder in placeholder_map.items():
                translated_text = translated_text.replace(placeholder_marker, placeholder)

            entry.msgstr = translated_text
            return entry
        except Exception as e:
            translation_error_flag = True
            logger.error(f"{self.file_name}: {e}")
            raise

    def _translate_entries_chunk(self, entries_chunk, config, no_cache):
        global shutdown_flag, translation_error_flag

        if shutdown_flag or translation_error_flag:
            logger.info("Shutting down translation due to interrupt signal or translation error.")
            return []

        translator = TranslatorFactory(config).get_translator_instance()
        cache_handler = (
            CacheHandler(os.path.join(os.path.expanduser("~"), ".translator_po", ".cache")) if not no_cache else None
        )

        translated_entries = []
        for entry in entries_chunk:
            if translation_error_flag:
                break

            translated_entries.append(self._translate_entry(entry, translator, cache_handler))

        return translated_entries

    def translate_po_file(self):
        global shutdown_flag, translation_error_flag
        if self.data:
            po = polib.pofile(self.data)
            entries = po.untranslated_entries()
            chunk_size = max(1, len(entries) // self.jobs)
            chunks = [entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)]

            with concurrent.futures.ProcessPoolExecutor(max_workers=self.jobs) as executor:
                worker_func = partial(self._translate_entries_chunk, config=self.config, no_cache=self.no_cache)
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
