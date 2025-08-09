#!/usr/bin/env python3
"""
元數據遷移腳本
Metadata Migration Script

將現有的元數據文件從 data/metadata/ 遷移到 data/output/metadata/
確保遷移過程安全可靠，支持回滾。
"""

import os
import sys
import shutil
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

def check_metadata_files(source_dir: Path) -> List[Path]:
    """檢查源目錄中的元數據文件"""
    metadata_files = []
    
    if not source_dir.exists():
        print(f"📁 源目錄不存在: {source_dir}")
        return metadata_files
    
    # 查找JSON元數據文件
    for file_path in source_dir.rglob("*.json"):
        metadata_files.append(file_path)
    
    # 查找其他可能的元數據文件
    for pattern in ["*.meta", "*.yml", "*.yaml"]:
        for file_path in source_dir.rglob(pattern):
            metadata_files.append(file_path)
    
    return metadata_files

def create_migration_plan(source_dir: Path, target_dir: Path) -> List[Dict[str, str]]:
    """創建遷移計劃"""
    migration_plan = []
    metadata_files = check_metadata_files(source_dir)
    
    for source_file in metadata_files:
        # 計算相對路徑
        relative_path = source_file.relative_to(source_dir)
        target_file = target_dir / relative_path
        
        migration_plan.append({
            "source": str(source_file),
            "target": str(target_file),
            "relative_path": str(relative_path),
            "size": source_file.stat().st_size if source_file.exists() else 0
        })
    
    return migration_plan

def execute_migration(migration_plan: List[Dict[str, str]], 
                     dry_run: bool = True,
                     create_backup: bool = True) -> Dict[str, int]:
    """執行遷移"""
    results = {
        "success": 0,
        "failed": 0,
        "skipped": 0
    }
    
    backup_dir = None
    if create_backup and not dry_run:
        backup_dir = Path("data/temp/metadata_backup")
        backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"📦 備份目錄: {backup_dir}")
    
    for item in migration_plan:
        source_path = Path(item["source"])
        target_path = Path(item["target"])
        
        try:
            if not source_path.exists():
                print(f"⚠️  源文件不存在: {source_path}")
                results["skipped"] += 1
                continue
            
            if target_path.exists():
                print(f"⚠️  目標文件已存在: {target_path}")
                results["skipped"] += 1
                continue
            
            if dry_run:
                print(f"[DRY RUN] {item['relative_path']} ({item['size']} bytes)")
                results["success"] += 1
            else:
                # 創建目標目錄
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 創建備份
                if backup_dir:
                    backup_path = backup_dir / item["relative_path"]
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, backup_path)
                
                # 複製文件
                shutil.copy2(source_path, target_path)
                print(f"✅ 遷移成功: {item['relative_path']}")
                results["success"] += 1
        
        except Exception as e:
            print(f"❌ 遷移失敗: {item['relative_path']} - {e}")
            results["failed"] += 1
    
    return results

def clean_old_metadata(source_dir: Path, migration_plan: List[Dict[str, str]]) -> int:
    """清理舊的元數據文件"""
    cleaned = 0
    
    for item in migration_plan:
        source_path = Path(item["source"])
        if source_path.exists():
            try:
                source_path.unlink()
                print(f"🗑️  已刪除: {item['relative_path']}")
                cleaned += 1
            except Exception as e:
                print(f"❌ 刪除失敗: {item['relative_path']} - {e}")
    
    # 清理空目錄
    try:
        if source_dir.exists() and not any(source_dir.iterdir()):
            source_dir.rmdir()
            print(f"🗑️  已刪除空目錄: {source_dir}")
    except Exception as e:
        print(f"❌ 刪除目錄失敗: {source_dir} - {e}")
    
    return cleaned

def save_migration_log(migration_plan: List[Dict[str, str]], 
                      results: Dict[str, int],
                      log_file: Path):
    """保存遷移日誌"""
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": results,
        "migration_plan": migration_plan
    }
    
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    print(f"📄 遷移日誌已保存: {log_file}")

def main():
    """主函數"""
    print("📁 元數據遷移腳本")
    print("=" * 50)
    
    # 配置路徑
    project_root = Path(__file__).parent.parent
    source_dir = project_root / "data" / "metadata"
    target_dir = project_root / "data" / "output" / "metadata"
    log_file = project_root / "data" / "temp" / "metadata_migration_log.json"
    
    print(f"📂 源目錄: {source_dir}")
    print(f"📂 目標目錄: {target_dir}")
    
    # 檢查元數據文件
    print("\n🔍 檢查元數據文件...")
    metadata_files = check_metadata_files(source_dir)
    
    if not metadata_files:
        print("✅ 沒有找到需要遷移的元數據文件")
        print("📁 目標目錄已是正確位置，無需遷移")
        return
    
    print(f"📋 找到 {len(metadata_files)} 個元數據文件")
    
    # 顯示文件列表
    print("\n📄 元數據文件列表:")
    for i, file_path in enumerate(metadata_files[:10], 1):
        relative_path = file_path.relative_to(source_dir)
        size = file_path.stat().st_size
        print(f"  {i}. {relative_path} ({size} bytes)")
    
    if len(metadata_files) > 10:
        print(f"  ... 還有 {len(metadata_files) - 10} 個文件")
    
    # 創建遷移計劃
    print("\n📋 創建遷移計劃...")
    migration_plan = create_migration_plan(source_dir, target_dir)
    
    # 詢問用戶操作
    print("\n❓ 選擇操作:")
    print("  1. 預覽遷移（不實際移動）")
    print("  2. 執行遷移（複製文件，保留源文件）")
    print("  3. 執行遷移並清理源文件")
    print("  4. 取消")
    
    try:
        choice = input("\n請選擇 (1-4): ").strip()
    except KeyboardInterrupt:
        print("\n❌ 操作已取消")
        return
    
    if choice == "1":
        # 預覽模式
        print("\n🔍 預覽遷移...")
        results = execute_migration(migration_plan, dry_run=True)
        
    elif choice == "2":
        # 執行遷移（保留源文件）
        print("\n🔄 執行遷移（保留源文件）...")
        results = execute_migration(migration_plan, dry_run=False, create_backup=True)
        
    elif choice == "3":
        # 執行遷移並清理
        print("\n⚠️  執行遷移並清理源文件")
        print("⚠️  這將刪除源目錄中的元數據文件！")
        confirm = input("輸入 'YES' 確認: ").strip()
        
        if confirm == "YES":
            print("🔄 執行遷移...")
            results = execute_migration(migration_plan, dry_run=False, create_backup=True)
            
            if results["failed"] == 0:
                print("🗑️  清理源文件...")
                cleaned = clean_old_metadata(source_dir, migration_plan)
                print(f"🗑️  已清理 {cleaned} 個文件")
        else:
            print("❌ 操作已取消")
            return
            
    else:
        print("❌ 操作已取消")
        return
    
    # 顯示結果
    print(f"\n📊 執行結果:")
    print(f"  ✅ 成功: {results['success']}")
    print(f"  ❌ 失敗: {results['failed']}")
    print(f"  ⏭️  跳過: {results['skipped']}")
    
    # 保存日誌
    save_migration_log(migration_plan, results, log_file)
    
    if results['failed'] == 0:
        print("🎉 元數據遷移完成！")
        print(f"📂 新的元數據位置: {target_dir}")
    else:
        print("⚠️  部分文件遷移失敗，請檢查日誌")

if __name__ == "__main__":
    main()
