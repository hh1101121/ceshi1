import sqlite3
import os
import threading
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path='app.db'):
        """
        初始化数据库管理器

        Args:
            db_path (str): 数据库文件路径
        """
        self.db_path = db_path
        self.connection = None
        self._local = threading.local()
        self.init_database()

    def get_connection(self):
        """
        获取当前线程的数据库连接对象

        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
        return self._local.connection

    def init_database(self):
        """
        初始化数据库，创建必要的表
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    count INTEGER DEFAULT 10, 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建文件记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    filename TEXT NOT NULL,
                    file_id TEXT,
                    file_type TEXT NOT NULL,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    record_time INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')

            conn.commit()
            print("数据库初始化完成")
        except Exception as e:
            print("数据库初始化失败:", e)


    def insert_file_record(self, file_id, filename, file_type,record_time, file_size=None, user_id=None):
        """
        插入文件记录

        Args:
            filename (str): 文件名
            file_id (str): 文件ID
            file_type: 文件类型
            record_time : 写入的记录日期
            user_id (int, optional): 用户ID，可为空

        Returns:
            int: 插入记录的ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 如果record_time是datetime对象，转换为时间戳
        if isinstance(record_time, datetime):
            record_time = int(record_time.timestamp())

        cursor.execute('''
                       INSERT INTO file_records (user_id, filename, file_id, file_type, record_time)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (user_id, filename, file_id, file_type, record_time))

        conn.commit()
        return cursor.lastrowid

    def close_connection(self):
        """
         关闭当前线程的数据库连接
        """
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection
