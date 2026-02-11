import os
import shutil
import time
import zipfile
import consts

class BackupService:
    def __init__(self, db_path: str = consts.MEMORY_DB_PATH, backup_dir: str = consts.BACKUPS_DIR):
        self.db_path = db_path
        self.backup_dir = backup_dir
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def create_backup(self):
        if not os.path.exists(self.db_path):
            print(f"   [!] Backup failed: DB path {self.db_path} does not exist.")
            return

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_name = f"fern_memory_backup_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_name)

        print(f"   [*] Creating Database Backup: {backup_name}...")
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.db_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Relative path for the zip
                        rel_path = os.path.relpath(file_path, os.path.dirname(self.db_path))
                        zipf.write(file_path, rel_path)
            
            print(f"   [+] Backup Successful: {backup_path}")
            self.cleanup_old_backups()
        except Exception as e:
            print(f"   [!] Backup Error: {e}")

    def cleanup_old_backups(self, max_backups: int = 5):
        try:
            backups = [os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.endswith(".zip")]
            backups.sort(key=os.path.getmtime)
            
            if len(backups) > max_backups:
                to_remove = backups[:-max_backups]
                for b in to_remove:
                    os.remove(b)
                    print(f"   [-] Removed old backup: {b}")
        except Exception as e:
            print(f"   [!] Cleanup Error: {e}")

# Singleton
backup_service = BackupService()
