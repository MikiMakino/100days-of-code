"""ftp/client.py - FTPClient（接続・RETR / STOR / LIST）"""

import ftplib
import os


class FTPClient:
    """FTP接続・操作クラス"""

    def __init__(self):
        self.ftp = None
        self.connected = False

    def connect(self, host, port, user, passwd, passive=True):
        self.ftp = ftplib.FTP()
        self.ftp.connect(host, int(port), timeout=15)
        self.ftp.login(user, passwd)
        self.ftp.set_pasv(passive)
        self.connected = True

    def disconnect(self):
        if self.ftp:
            try:
                self.ftp.quit()
            except Exception:
                pass
        self.ftp = None
        self.connected = False

    def list_dir(self, path="."):
        items = []
        try:
            lines = []
            self.ftp.retrlines(f"LIST {path}", lines.append)
            for line in lines:
                parts = line.split(None, 8)
                if len(parts) < 9:
                    continue
                perms = parts[0]
                size  = parts[4]
                name  = parts[8]
                is_dir = perms.startswith("d")
                items.append({"name": name, "is_dir": is_dir, "size": size, "perms": perms})
        except Exception:
            pass
        return items

    def download(self, remote_path, local_path, callback=None):
        with open(local_path, "wb") as f:
            def write(data):
                f.write(data)
                if callback:
                    callback(len(data))
            self.ftp.retrbinary(f"RETR {remote_path}", write)

    def upload(self, local_path, remote_path, callback=None):
        file_size = os.path.getsize(local_path)
        with open(local_path, "rb") as f:
            def read_callback(data):
                if callback:
                    callback(len(data))
            self.ftp.storbinary(f"STOR {remote_path}", f, 8192, read_callback)
        return file_size

    def download_dsn(self, dsn, local_path, callback=None):
        """データセット名を直接指定してダウンロード: RETR 'DSN'"""
        remote = f"'{dsn}'"
        with open(local_path, "wb") as f:
            def write(data):
                f.write(data)
                if callback:
                    callback(len(data))
            self.ftp.retrbinary(f"RETR {remote}", write)

    def upload_dsn(self, local_path, dsn, callback=None):
        """データセット名を直接指定してアップロード: STOR 'DSN'"""
        remote = f"'{dsn}'"
        with open(local_path, "rb") as f:
            def read_callback(data):
                if callback:
                    callback(len(data))
            self.ftp.storbinary(f"STOR {remote}", f, 8192, read_callback)

    def download_gdg(self, dsn, local_path, callback=None):
        """GDG最新世代をダウンロード: RETR 'DSN(0)'"""
        remote = f"'{dsn}(0)'"
        with open(local_path, "wb") as f:
            def write(data):
                f.write(data)
                if callback:
                    callback(len(data))
            self.ftp.retrbinary(f"RETR {remote}", write)

    def mkdir(self, path):
        self.ftp.mkd(path)

    def delete_file(self, path):
        self.ftp.delete(path)

    def delete_dir(self, path):
        self.ftp.rmd(path)

    def rename(self, old, new):
        self.ftp.rename(old, new)

    def pwd(self):
        return self.ftp.pwd()

    def cwd(self, path):
        self.ftp.cwd(path)
