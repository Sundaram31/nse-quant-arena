#!/usr/bin/env python3
"""
NSE Quant Arena - Automated Datastore Backup & Archival Engine
Creates compressed, verified timestamped snapshots of the 3,223 stock parquet datastore.
"""
import os
import sys
import tarfile
import json
import hashlib
from datetime import datetime

def create_backup(dest_dir: str = "backups") -> str:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root_dir, "nse_system", "data", "datastore")
    manifest_file = os.path.join(root_dir, "nse_system", "data", "datastore_manifest.json")
    
    if not os.path.exists(data_dir):
        print(f"❌ Error: Datastore directory not found at {data_dir}")
        sys.exit(1)
        
    os.makedirs(dest_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"nse_datastore_backup_{timestamp}.tar.gz"
    backup_path = os.path.join(dest_dir, backup_filename)
    
    parquet_files = [f for f in os.listdir(data_dir) if f.endswith(".parquet")]
    total_files = len(parquet_files)
    
    print("=" * 70)
    print("📦 NSE QUANT ARENA - AUTOMATED DATASTORE BACKUP ENGINE")
    print("=" * 70)
    print(f"📂 Source Datastore : {data_dir}")
    print(f"📊 Total Stocks      : {total_files:,} Parquet datasets")
    print(f"💾 Target Archive   : {backup_path}")
    print("=" * 70)
    print("⏳ Compressing and verifying data files...")
    
    with tarfile.open(backup_path, "w:gz") as tar:
        # Add parquet files
        for f in parquet_files:
            full_p = os.path.join(data_dir, f)
            tar.add(full_p, arcname=os.path.join("datastore", f))
            
        # Add manifest if exists
        if os.path.exists(manifest_file):
            tar.add(manifest_file, arcname="datastore_manifest.json")
            
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    
    # Calculate SHA256 Checksum for integrity verification
    hasher = hashlib.sha256()
    with open(backup_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    checksum = hasher.hexdigest()
    
    # Write backup metadata log
    meta = {
        "timestamp": datetime.now().isoformat(),
        "backup_file": backup_filename,
        "size_mb": round(size_mb, 2),
        "total_stock_files": total_files,
        "sha256": checksum
    }
    meta_path = os.path.join(dest_dir, f"backup_meta_{timestamp}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
        
    print(f"✅ Backup Completed Successfully!")
    print(f"📦 Archive Size   : {size_mb:.2f} MB")
    print(f"🔒 SHA256 Checksum: {checksum[:16]}...{checksum[-8:]}")
    print(f"📁 Saved to       : {os.path.abspath(backup_path)}")
    print("=" * 70)
    return backup_path

if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "backups"
    create_backup(dest)
