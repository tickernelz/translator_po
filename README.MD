# Translator PO

Translator PO is a Python-based tool designed to translate `.po` and `.pot` files using various translation services. It supports multiple translators like Google, Microsoft, Deepl, and more, allowing for flexible and efficient translation of localization files.

## Features

- Supports multiple translation services.
- Handles placeholders in translation strings.
- Concurrent translation for faster processing.
- Customizable configuration for different translators.
- Supports Odoo output format.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/tickernelz/translator_po.git
    cd translator_po
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Configuration

Create a `config.json` file in the root directory of the project. You can use the default configuration provided in the code:

```json
{
    "translator": "GoogleTranslator",
    "source_lang": "id",
    "target_lang": "en",
    "max_msgid_length": 300,
    "DeeplTranslator": {"api_key": "", "use_free_api": true},
    "QcriTranslator": {"api_key": ""},
    "YandexTranslator": {"api_key": ""},
    "MicrosoftTranslator": {"api_key": "", "region": ""},
    "LibreTranslator": {"api_key": "", "use_free_api": true, "custom_url": ""},
    "PapagoTranslator": {"client_id": "", "secret_key": ""},
    "ChatGptTranslator": {"api_key": "", "model": "gpt-3.5-turbo"},
    "BaiduTranslator": {"appid": "", "appkey": ""}
}
```

Usage
-----

### Command Line Interface

You can use the command line interface to translate `.po` or `.pot` files.

1.  Translate a single file:

    `python main.py --file_path path/to/your/file.po output_folder path/to/output/folder config_file path/to/config.json`

2.  Translate all files in a folder:

    `python main.py --folder_path path/to/your/folder output_folder path/to/output/folder config_file path/to/config.json`

3.  Enable Odoo output format:

    `python main.py --file_path path/to/your/file.po output_folder path/to/output/folder config_file path/to/config.json --odoo_output`

### Example

`python main.py --file_path example.po output_folder translations config_file config.json`

Logging
-------

The tool uses Python's built-in logging module to log information, warnings, and errors. Logs include timestamps for better traceability.

Contributing
------------

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature-branch`).
3.  Make your changes.
4.  Commit your changes (`git commit -am 'Add new feature'`).
5.  Push to the branch (`git push origin feature-branch`).
6.  Create a new Pull Request.

License
-------

This project is licensed under the MIT License. See the `LICENSE` file for more details.

Acknowledgements
----------------

-   [polib](jetbrains://browser://https://github.com/izimobil/polib) for handling `.po` files.
-   [deep-translator](jetbrains://browser://https://github.com/nidhaloff/deep-translator) for providing multiple translation services.
-   [tqdm](jetbrains://browser://https://github.com/tqdm/tqdm) for progress bars.