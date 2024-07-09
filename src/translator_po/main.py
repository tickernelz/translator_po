import argparse
import logging
import os
import signal

import colorlog

from .config_handler import ConfigHandler
from .po_file_merger import PoFileMerger
from .po_file_processor import PoFileProcessor
from .po_file_splitter import PoFileSplitter

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


class MainController:
    def __init__(self, args):
        self.args = args
        cli_config_path = args.config_file if args.config_file else None
        self.config_handler = ConfigHandler(args.config_file or 'config.json', cli_config_path)
        self.jobs = args.jobs
        self.force = args.force
        self.no_cache = args.no_cache
        self.file_processors = []

    def process_file(self, file_path, output_folder, odoo_output):
        processor = PoFileProcessor(
            file_path, self.config_handler.config, output_folder, odoo_output, self.jobs, self.force, self.no_cache
        )
        processor.process()

    def process_files_in_folder(self, folder_path, output_folder, odoo_output):
        global shutdown_flag, translation_error_flag
        files = sorted(
            [
                os.path.join(folder_path, file_name)
                for file_name in os.listdir(folder_path)
                if file_name.endswith('.po') or file_name.endswith('.pot')
            ]
        )

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
    parser.add_argument('-c', '--config_file', type=str, help='Path to the configuration file')
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
    parser.add_argument('-nc', '--no_cache', action='store_true', help='Disable caching of translations')

    args = parser.parse_args()

    controller = MainController(args)
    controller.run()


if __name__ == "__main__":
    main()
