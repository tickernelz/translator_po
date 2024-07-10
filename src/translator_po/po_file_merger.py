import logging
import os

import polib

logger = logging.getLogger(__name__)


class PoFileMerger:
    def __init__(self, folder_path, output_file):
        self.folder_path = folder_path
        self.output_file = output_file

    def merge_po_files(self):
        merged_po = polib.POFile()
        for root, _, files in os.walk(self.folder_path):
            for file_name in files:
                if file_name.endswith('.po'):
                    file_path = os.path.join(root, file_name)
                    po = polib.pofile(file_path)
                    merged_po.extend(po)
        merged_po.save(self.output_file)
        logger.info(f"Merged file saved: {self.output_file}")