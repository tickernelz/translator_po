import hashlib
import logging
import os
import sqlite3
from threading import local

logger = logging.getLogger(__name__)
class CacheHandler:
    MAX_CACHE_SIZE = 1 * 1024 * 1024  # 4MB

    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.local = local()
        self._initialize_cache()

    def _initialize_cache(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        self._open_new_cache_file()

    def _open_new_cache_file(self):
        cache_files = sorted(
            [f for f in os.listdir(self.cache_dir) if f.startswith('cache_') and f.endswith('.db')],
            key=lambda x: int(x.split('_')[1].split('.')[0]),
        )
        if cache_files:
            last_cache_file = cache_files[-1]
            self.db_path = os.path.join(self.cache_dir, last_cache_file)
            if os.path.getsize(self.db_path) >= self.MAX_CACHE_SIZE:
                new_cache_index = int(last_cache_file.split('_')[1].split('.')[0]) + 1
                self.db_path = os.path.join(self.cache_dir, f'cache_{new_cache_index}.db')
        else:
            self.db_path = os.path.join(self.cache_dir, 'cache_0.db')

    def _get_connection(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path)
            self.local.cursor = self.local.conn.cursor()
            self.local.cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS translations (
                    id TEXT PRIMARY KEY,
                    source_lang TEXT,
                    target_lang TEXT,
                    translator TEXT,
                    source_text TEXT,
                    translated_text TEXT
                )
            '''
            )
            self.local.conn.commit()
        return self.local.conn, self.local.cursor

    def _generate_cache_key(self, source_lang, target_lang, translator, source_text):
        key = f"{source_lang}:{target_lang}:{translator}:{source_text}"
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def get_translation(self, source_lang, target_lang, translator, source_text):
        conn, cursor = self._get_connection()
        cache_key = self._generate_cache_key(source_lang, target_lang, translator, source_text)
        cursor.execute(
            '''
            SELECT translated_text FROM translations WHERE id = ?
        ''',
            (cache_key,),
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def save_translation(self, source_lang, target_lang, translator, source_text, translated_text):
        conn, cursor = self._get_connection()
        cache_key = self._generate_cache_key(source_lang, target_lang, translator, source_text)
        cursor.execute(
            '''
            INSERT OR REPLACE INTO translations (id, source_lang, target_lang, translator, source_text, translated_text)
            VALUES (?, ?, ?, ?, ?, ?)
        ''',
            (cache_key, source_lang, target_lang, translator, source_text, translated_text),
        )
        conn.commit()
        if os.path.getsize(self.db_path) >= self.MAX_CACHE_SIZE:
            self._open_new_cache_file()
            self.local.conn = None  # Force new connection in next call
