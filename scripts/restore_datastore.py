#!/usr/bin/env python3
"""
NSE Quant Arena - Datastore Restoration Engine
Restores the 3,223 stock parquet datastore from a compressed backup archive.
"""
import os
import sys
import tarfile
import glob

def restore_backup(backup_file: str = None) -> bool:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_data_dir = os.path.join(root_dir, "nse_system", "data", "datastore")
    target_manifest = os.path.join(root_dir, "nse_system", "data")
    
    if not backup_file:
        backups = sorted(glob.glob(os.path.join(root_dir, "backups", "nse_datastore_backup_*.tar.gz")))
        if not backups:
            print("❌ No backup archives found in 'backups/' directory.")
            return False
        backup_file = backups[-1]  # Latest backup
        
    if not os.path.exists(backup_file):
        print(f"❌ Backup archive not found: {backup_file}")
        return False
        
    print("=" * 70)
    print("🔄 NSE QUANT ARENA - DATASTORE RESTORATION ENGINE")
    print("=" * 70)
    print(f"📦 Archive Source : {backup_file}")
    print(f"📂 Target Dir     : {target_data_dir}")
    print("=" * 70)
    print("⏳ Extracting files...")
    
    os.makedirs(target_data_dir, exist_ok=True)
    
    extracted_count = 0
    with tarfile.open(backup_file, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name.startswith("datastore/") and member.name.endswith(".parquet"):
                member.name = os.path.basename(member.name)
                tar.extract(member, path=target_data_dir)
                extracted_count += 1
            elif member.name == "datastore_manifest.json":
                tar.extract(member, path=target_manifest)
                
    print(f"✅ Restoration Complete: {extracted_count:,} stock datasets restored successfully!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    b_file = sys.argv[1] if len(sys.argv) > 1 else None
    restore_backup(b_file)
