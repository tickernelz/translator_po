Translator PO
=============

This project is a command-line tool for translating `.po` and `.pot` files using various translation services. It
supports multiple translators and can handle placeholders in the text.

Features
--------

- Supports multiple translators including Google, Microsoft, Deepl, and more.
- Handles placeholders in the text to ensure they are not altered during translation.
- Can process individual files or entire folders.
- Supports custom configuration through a JSON file.
- Option to output in Odoo format.
- Uses `tqdm` for progress reporting.
- Supports multiprocessing for faster translation.

Installation
------------

1. Clone the repository:

   ```console
   git clone https://github.com/tickernelz/translator_po.git
   ```
   ```console
   cd translator_po
   ```

2. Install the required dependencies:

   ```console
   pip install -r requirements.txt
   ```

3. Install the package as a pip module:

   ```console
   pip install .
   ```

Usage
-----

### Command-Line Arguments

- `-f`, `--file_path`: Path to the input `.po` or `.pot` file.
- `-d`, `--folder_path`: Path to the folder containing `.po` or `.pot` files.
- `-o`, `--output_folder`: Path to the output folder.
- `-c`, `--config_file`: Path to the configuration file (default: `config.json`).
- `-O`, `--odoo_output`: Enable Odoo output format.

### Examples

#### Translate a Single File

```console
translator_po -f path/to/your/file.po -o path/to/output/folder
```

#### Translate All Files in a Folder

```console
translator_po -d path/to/your/folder -o path/to/output/folder
```

#### Use a Custom Configuration File

```console
translator_po -f path/to/your/file.po -o path/to/output/folder -c path/to/config.json
```

#### Enable Odoo Output Format

```console
translator_po -f path/to/your/file.po -o path/to/output/folder -O
```

Configuration
-------------

The configuration file is a JSON file that specifies the translator settings. If the configuration file does not exist,
a default configuration will be created in the home directory under `.translator_po`.

### Default Configuration

```json
{
  "translator": "GoogleTranslator",
  "source_lang": "id",
  "target_lang": "en",
  "max_msgid_length": 300,
  "DeeplTranslator": {
    "api_key": "",
    "use_free_api": true
  },
  "QcriTranslator": {
    "api_key": ""
  },
  "YandexTranslator": {
    "api_key": ""
  },
  "MicrosoftTranslator": {
    "api_key": "",
    "region": ""
  },
  "LibreTranslator": {
    "api_key": "",
    "use_free_api": true,
    "custom_url": ""
  },
  "PapagoTranslator": {
    "client_id": "",
    "secret_key": ""
  },
  "ChatGptTranslator": {
    "api_key": "",
    "model": "gpt-3.5-turbo"
  },
  "BaiduTranslator": {
    "appid": "",
    "appkey": ""
  }
}
```

Logging
-------

The program uses logging to provide information about its progress and any errors that occur. Logs include timestamps
and log levels for better readability.

Contributing
------------

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Create a new Pull Request.

License
-------

This project is licensed under the MIT License. See the `LICENSE` file for more details.

Contact
-------

For any questions or suggestions, please open an issue or contact the maintainer.