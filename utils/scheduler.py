import threading
import time
import sqlite3
from datetime import datetime, timedelta

class FileCleanupScheduler:
    def __init__(self, db_manager, client, interval=60,wait_time=3):
        """
        初始化定时清理任务

        Args:
            db_manager: 数据库管理器实例
            client: 【Quark客户端实例,百度客户端】
            interval: 检查间隔时间（秒），默认60秒
        """
        self.db_manager = db_manager
        self.client = client
        self.interval = interval
        self.wait_time = wait_time
        self.running = False
        self.thread = None
        self.lock = threading.Lock()


    def start(self):
        """
        启动定时清理任务
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            print("文件清理定时任务已启动")

    def stop(self):
        """
        停止定时清理任务
        """
        self.running = False
        if self.thread:
            self.thread.join()
        print("文件清理定时任务已停止")

    def _run(self):
        """
        定时任务运行逻辑
        """
        while self.running:
            try:
                self._cleanup_expired_files()
                time.sleep(self.interval)
            except Exception as e:
                print(f"清理任务执行出错: {e}")

    def _cleanup_expired_files(self):
        """
        清理过期文件
        """
        with self.lock:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()

            # 计算3分钟前的时间
            expired_timestamp = int((datetime.now() - timedelta(minutes=self.wait_time)).timestamp())
            print(f"expired_time的类型 是: {type(expired_timestamp)}")

            # 查询过期的文件记录
            cursor.execute('''
                SELECT id, file_id, record_time,file_type,filename 
                FROM file_records 
                WHERE record_time < ?
            ''', (int(expired_timestamp),) )

            expired_files = cursor.fetchall()

            if expired_files:
                print(f"发现{len(expired_files)}个过期文件需要清理")

                for file_record in expired_files:
                    record_id, file_id, record_time, file_type,file_name = file_record
                    print(f"DEBUG: record_id 类型={type(record_id)}, 值={record_id}")
                    print(f"DEBUG: record_time 类型={type(record_time)}, 值={record_time}")
                    print(f"DEBUG: expired_time 类型={type(expired_timestamp)}, 值={expired_timestamp}")

                    if isinstance(record_time, str):
                        print(f"WARNING: record_time 是字符串格式: {record_time}")
                        try:
                            record_time = int(record_time)
                        except ValueError:
                            print(f"无法将record_time转换为整数: {record_time}")
                            continue
                    # 确保数值类型的正确转换
                    record_id = int(record_id) if isinstance(record_id, str) else record_id

                    # 字符串比较时确保都是字符串类型
                    file_id = str(file_id)
                    try:
                        if file_type == "quark":
                            # 调用Quark类删除文件
                            if self.client[0].delete_file(file_id):
                                # 删除成功后从数据库中移除记录
                                cursor.execute('DELETE FROM file_records WHERE id = ?', (record_id,))
                                conn.commit()
                                print(f"文件 {file_id} 已成功删除并清理记录")
                            else:
                                print(f"文件 {file_id} 删除失败")
                        elif file_type == "baidu":
                            # 待实现
                            if self.client[1].delete_file(file_name):
                                # 删除成功后从数据库中移除记录
                                cursor.execute('DELETE FROM file_records WHERE id = ?', (record_id,))
                                conn.commit()
                                print(f"文件 {file_id} 已成功删除并清理记录")
                            else:
                                print(f"文件 {file_id} 删除失败")

                    except Exception as e:
                        print(f"处理文件 {file_id} 时出错: {type(e).__name__}: {e}")
                        import traceback
                        traceback.print_exc()
            else:
                print("没有发现过期文件")
