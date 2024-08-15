import logging
import os

import polib

logger = logging.getLogger(__name__)


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
        if not self.data:
            return

        po = polib.pofile(self.data)
        entries = po.untranslated_entries()
        chunk_size = max(1, len(entries) // self.num_split)
        chunks = [entries[i: i + chunk_size] for i in range(0, len(entries), chunk_size)]

        # Calculate the width for zero-padding
        width = len(str(self.num_split))

        for i, chunk in enumerate(chunks):
            split_po = polib.POFile()
            split_po.extend(chunk)

            # Format the output file name with zero-padding
            output_file_name = f"{os.path.splitext(self.file_name)[0]}_part_{str(i + 1).zfill(width)}.po"
            output_file_path = os.path.join(self.output_folder, output_file_name)

            os.makedirs(self.output_folder, exist_ok=True)
            split_po.save(output_file_path)
            logger.info(f"Saved split file: {output_file_path}")
