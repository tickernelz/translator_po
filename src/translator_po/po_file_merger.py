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
        for file_name in os.listdir(self.folder_path):
            if file_name.endswith('.po'):
                file_path = os.path.join(self.folder_path, file_name)
                po = polib.pofile(file_path)
                merged_po.extend(po)
        merged_po.save(self.output_file)
        logger.info(f"Merged file saved: {self.output_file}")
