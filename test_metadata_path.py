#!/usr/bin/env python3
"""
元數據路徑測試
Metadata Path Test

驗證元數據路徑統一化後的配置是否正確
"""

import sys
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_metadata_paths():
    """測試元數據路徑配置"""
    
    print("🧪 測試元數據路徑配置...")
    
    try:
        # 測試配置設置
        from config.settings import get_settings
        settings = get_settings()
        
        print(f"📂 配置中的元數據路徑: {settings.storage.metadata_storage_path}")
        
        # 測試元數據管理器
        from image_processing.metadata import ImageMetadataManager
        
        # 使用默認路徑
        manager_default = ImageMetadataManager()
        print(f"📂 元數據管理器默認路徑: {manager_default.storage_path}")
        
        # 使用配置路徑
        manager_config = ImageMetadataManager(settings.storage.metadata_storage_path)
        print(f"📂 元數據管理器配置路徑: {manager_config.storage_path}")
        
        # 驗證路徑是否一致
        expected_path = Path("data/output/metadata")
        
        if manager_default.storage_path == expected_path:
            print("✅ 默認路徑正確")
        else:
            print(f"❌ 默認路徑錯誤: 期望 {expected_path}, 實際 {manager_default.storage_path}")
        
        if Path(settings.storage.metadata_storage_path) == expected_path:
            print("✅ 配置路徑正確")
        else:
            print(f"❌ 配置路徑錯誤: 期望 {expected_path}, 實際 {settings.storage.metadata_storage_path}")
        
        # 檢查目錄是否存在
        if expected_path.exists():
            print(f"✅ 元數據目錄存在: {expected_path}")
            
            # 檢查是否有文件
            files = list(expected_path.glob("*.json"))
            print(f"📄 找到 {len(files)} 個元數據文件")
            
            if files:
                print("📋 元數據文件示例:")
                for file_path in files[:3]:
                    print(f"  - {file_path.name}")
                
                if len(files) > 3:
                    print(f"  ... 還有 {len(files) - 3} 個文件")
        else:
            print(f"⚠️  元數據目錄不存在: {expected_path}")
        
        # 檢查舊目錄是否還有文件
        old_path = Path("data/metadata")
        if old_path.exists():
            old_files = list(old_path.glob("*.json"))
            if old_files:
                print(f"⚠️  舊目錄仍有 {len(old_files)} 個文件: {old_path}")
            else:
                print(f"✅ 舊目錄已清空: {old_path}")
        else:
            print(f"✅ 舊目錄不存在: {old_path}")
        
        print("\n🎉 元數據路徑配置測試完成！")
        return True
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_metadata_paths()
    exit(0 if success else 1)
