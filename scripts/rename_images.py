#!/usr/bin/env python3
"""
圖片重命名腳本
Image Rename Script

將現有的圖片文件重命名為統一的規格標準格式：
{文件名}_{頁碼}_{圖片序號}_{時間戳}.{格式}

支援批量處理和安全回滾。
"""

import os
import re
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
from datetime import datetime

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.config.logging_config import get_logger
    logger = get_logger("rename_images")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("rename_images")

def analyze_current_naming_patterns(images_dir: Path) -> Dict[str, List[Path]]:
    """分析當前的命名模式"""
    patterns = {
        "correct_format": [],      # 正確格式：document_p001_img001_timestamp.ext
        "missing_page": [],        # 缺少頁碼：document_img_001_hash.ext
        "old_format": [],          # 舊格式：page_001_img_001_timestamp.ext
        "unknown": []              # 未知格式
    }
    
    if not images_dir.exists():
        logger.warning(f"圖片目錄不存在: {images_dir}")
        return patterns
    
    # 定義模式
    correct_pattern = re.compile(r'^(.+)_p(\d{3})_img(\d{3})_(\d+)\.(.+)$')
    missing_page_pattern = re.compile(r'^(.+)_img_(\d{3})_([a-f0-9]+)\.(.+)$')
    old_format_pattern = re.compile(r'^page_(\d{3})_img_(\d{3})_(\d+)\.(.+)$')
    
    # 遞歸搜索所有圖片文件
    for file_path in images_dir.rglob("*.png"):
        filename = file_path.name
        
        if correct_pattern.match(filename):
            patterns["correct_format"].append(file_path)
        elif missing_page_pattern.match(filename):
            patterns["missing_page"].append(file_path)
        elif old_format_pattern.match(filename):
            patterns["old_format"].append(file_path)
        else:
            patterns["unknown"].append(file_path)
    
    # 同樣處理其他格式
    for ext in ["*.jpg", "*.jpeg", "*.gif", "*.webp"]:
        for file_path in images_dir.rglob(ext):
            filename = file_path.name
            
            if correct_pattern.match(filename):
                patterns["correct_format"].append(file_path)
            elif missing_page_pattern.match(filename):
                patterns["missing_page"].append(file_path)
            elif old_format_pattern.match(filename):
                patterns["old_format"].append(file_path)
            else:
                patterns["unknown"].append(file_path)
    
    return patterns

def extract_info_from_filename(file_path: Path) -> Optional[Dict[str, str]]:
    """從文件名中提取信息"""
    filename = file_path.name
    
    # 嘗試匹配不同的模式
    patterns = [
        # 缺少頁碼的格式：workflows_img_001_aa542fa9.png
        (r'^(.+)_img_(\d+)_([a-f0-9]+)\.(.+)$', {
            'doc_name': 1, 'img_index': 2, 'hash': 3, 'ext': 4
        }),
        # 舊格式：page_001_img_001_timestamp.ext
        (r'^page_(\d+)_img_(\d+)_(\d+)\.(.+)$', {
            'page': 1, 'img_index': 2, 'timestamp': 3, 'ext': 4
        }),
        # 其他可能的格式
        (r'^(.+)_(\d+)\.(.+)$', {
            'doc_name': 1, 'img_index': 2, 'ext': 3
        })
    ]
    
    for pattern, groups in patterns:
        match = re.match(pattern, filename)
        if match:
            info = {}
            for key, group_idx in groups.items():
                info[key] = match.group(group_idx)
            
            # 補充缺失的信息
            if 'doc_name' not in info:
                info['doc_name'] = 'unknown_document'
            if 'page' not in info:
                info['page'] = '001'  # 默認頁碼
            if 'img_index' not in info:
                info['img_index'] = '001'  # 默認圖片索引
            if 'timestamp' not in info:
                info['timestamp'] = str(int(datetime.now().timestamp()))
            
            return info
    
    return None

def generate_new_filename(info: Dict[str, str]) -> str:
    """生成新的標準文件名"""
    doc_name = info['doc_name']
    page = info['page'].zfill(3)  # 確保3位數
    img_index = info['img_index'].zfill(3)  # 確保3位數
    timestamp = info['timestamp']
    ext = info['ext']
    
    return f"{doc_name}_p{page}_img{img_index}_{timestamp}.{ext}"

def create_rename_plan(patterns: Dict[str, List[Path]]) -> List[Dict[str, str]]:
    """創建重命名計劃"""
    rename_plan = []
    
    # 處理需要重命名的文件
    files_to_rename = patterns["missing_page"] + patterns["old_format"] + patterns["unknown"]
    
    for file_path in files_to_rename:
        info = extract_info_from_filename(file_path)
        if info:
            new_filename = generate_new_filename(info)
            new_path = file_path.parent / new_filename
            
            # 檢查新文件名是否已存在
            if new_path.exists() and new_path != file_path:
                # 如果已存在，添加一個計數器
                name_part, ext = new_filename.rsplit('.', 1)
                counter = 1
                while new_path.exists():
                    new_filename = f"{name_part}_{counter:02d}.{ext}"
                    new_path = file_path.parent / new_filename
                    counter += 1
            
            rename_plan.append({
                "old_path": str(file_path),
                "new_path": str(new_path),
                "old_name": file_path.name,
                "new_name": new_path.name,
                "reason": "統一命名格式"
            })
    
    return rename_plan

def execute_rename_plan(rename_plan: List[Dict[str, str]], 
                       dry_run: bool = True,
                       backup_dir: Optional[Path] = None) -> Dict[str, int]:
    """執行重命名計劃"""
    results = {
        "success": 0,
        "failed": 0,
        "skipped": 0
    }
    
    if backup_dir and not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
    
    for item in rename_plan:
        old_path = Path(item["old_path"])
        new_path = Path(item["new_path"])
        
        try:
            if not old_path.exists():
                logger.warning(f"源文件不存在: {old_path}")
                results["skipped"] += 1
                continue
            
            if old_path == new_path:
                logger.debug(f"文件名無需更改: {old_path.name}")
                results["skipped"] += 1
                continue
            
            if dry_run:
                logger.info(f"[DRY RUN] {old_path.name} → {new_path.name}")
                results["success"] += 1
            else:
                # 創建備份（如果需要）
                if backup_dir:
                    backup_path = backup_dir / old_path.name
                    shutil.copy2(old_path, backup_path)
                    logger.debug(f"備份創建: {backup_path}")
                
                # 執行重命名
                old_path.rename(new_path)
                logger.info(f"重命名成功: {old_path.name} → {new_path.name}")
                results["success"] += 1
        
        except Exception as e:
            logger.error(f"重命名失敗: {old_path.name} → {new_path.name}, 錯誤: {e}")
            results["failed"] += 1
    
    return results

def save_rename_log(rename_plan: List[Dict[str, str]], 
                   results: Dict[str, int],
                   log_file: Path):
    """保存重命名日誌"""
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": results,
        "plan": rename_plan
    }
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"重命名日誌已保存: {log_file}")

def main():
    """主函數"""
    print("🖼️ 圖片重命名腳本")
    print("=" * 50)
    
    # 配置路徑
    project_root = Path(__file__).parent.parent
    images_dir = project_root / "data" / "output" / "images"
    backup_dir = project_root / "data" / "temp" / "image_backup"
    log_file = project_root / "data" / "temp" / "rename_log.json"
    
    # 確保目錄存在
    backup_dir.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 分析當前命名模式
    print("🔍 分析當前圖片命名模式...")
    patterns = analyze_current_naming_patterns(images_dir)
    
    print(f"📊 分析結果:")
    print(f"  ✅ 正確格式: {len(patterns['correct_format'])} 個")
    print(f"  ⚠️  缺少頁碼: {len(patterns['missing_page'])} 個")
    print(f"  📰 舊格式: {len(patterns['old_format'])} 個")
    print(f"  ❓ 未知格式: {len(patterns['unknown'])} 個")
    
    if not any(len(files) > 0 for files in [patterns['missing_page'], patterns['old_format'], patterns['unknown']]):
        print("🎉 所有圖片已使用正確的命名格式！")
        return
    
    # 創建重命名計劃
    print("\n📋 創建重命名計劃...")
    rename_plan = create_rename_plan(patterns)
    
    if not rename_plan:
        print("✅ 無需重命名任何文件")
        return
    
    print(f"📝 計劃重命名 {len(rename_plan)} 個文件")
    
    # 顯示前5個示例
    print("\n📄 重命名示例（前5個）:")
    for item in rename_plan[:5]:
        print(f"  {item['old_name']} → {item['new_name']}")
    
    if len(rename_plan) > 5:
        print(f"  ... 還有 {len(rename_plan) - 5} 個文件")
    
    # 詢問用戶確認
    print("\n❓ 選擇操作:")
    print("  1. 預覽模式（不實際重命名）")
    print("  2. 執行重命名（帶備份）")
    print("  3. 執行重命名（不備份）")
    print("  4. 取消")
    
    try:
        choice = input("\n請選擇 (1-4): ").strip()
    except KeyboardInterrupt:
        print("\n❌ 操作已取消")
        return
    
    if choice == "1":
        # 預覽模式
        print("\n🔍 預覽模式執行中...")
        results = execute_rename_plan(rename_plan, dry_run=True)
        
    elif choice == "2":
        # 執行重命名（帶備份）
        print("\n🔄 執行重命名（帶備份）...")
        results = execute_rename_plan(rename_plan, dry_run=False, backup_dir=backup_dir)
        
    elif choice == "3":
        # 執行重命名（不備份）
        print("\n⚠️  確認執行重命名（不備份）？輸入 'YES' 確認: ", end="")
        confirm = input().strip()
        if confirm == "YES":
            print("🔄 執行重命名（不備份）...")
            results = execute_rename_plan(rename_plan, dry_run=False)
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
    save_rename_log(rename_plan, results, log_file)
    
    if results['failed'] == 0:
        print("🎉 圖片重命名完成！")
    else:
        print("⚠️  部分文件重命名失敗，請檢查日誌")

if __name__ == "__main__":
    main()
