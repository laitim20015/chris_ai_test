"""
測試運行腳本

提供統一的測試執行入口，支持不同類型的測試運行。
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], description: str) -> bool:
    """
    運行命令並顯示結果
    
    Args:
        cmd: 命令列表
        description: 命令描述
        
    Returns:
        是否成功
    """
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("警告:", result.stderr)
        print(f"✅ {description} - 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - 失敗")
        print("錯誤輸出:", e.stderr)
        print("標準輸出:", e.stdout)
        return False


def run_unit_tests(verbose: bool = False, coverage: bool = True) -> bool:
    """運行單元測試"""
    cmd = ["python", "-m", "pytest", "tests/unit/", "-m", "unit"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    
    return run_command(cmd, "運行單元測試")


def run_integration_tests(verbose: bool = False) -> bool:
    """運行集成測試"""
    cmd = ["python", "-m", "pytest", "tests/integration/", "-m", "integration"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "運行集成測試")


def run_api_tests(verbose: bool = False) -> bool:
    """運行API測試"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "api"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "運行API測試")


def run_parser_tests(verbose: bool = False) -> bool:
    """運行解析器測試"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "parser"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "運行解析器測試")


def run_association_tests(verbose: bool = False) -> bool:
    """運行關聯分析測試"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "association"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "運行關聯分析測試")


def run_slow_tests(verbose: bool = False) -> bool:
    """運行慢速測試"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "slow", "--runslow"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "運行慢速測試")


def run_azure_tests(verbose: bool = False) -> bool:
    """運行Azure OpenAI測試（需要配置）"""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "azure", "--runazure"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "運行Azure OpenAI測試")


def run_all_tests(verbose: bool = False, coverage: bool = True, include_slow: bool = False) -> bool:
    """運行所有測試"""
    cmd = ["python", "-m", "pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-report=html"])
    
    if include_slow:
        cmd.append("--runslow")
    
    return run_command(cmd, "運行所有測試")


def run_specific_test(test_path: str, verbose: bool = False) -> bool:
    """運行特定測試文件"""
    cmd = ["python", "-m", "pytest", test_path]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, f"運行測試: {test_path}")


def check_test_environment() -> bool:
    """檢查測試環境"""
    print("🔍 檢查測試環境...")
    
    # 檢查Python版本
    python_version = sys.version_info
    if python_version < (3, 9):
        print(f"❌ Python版本過低: {python_version.major}.{python_version.minor}")
        print("需要Python 3.9或更高版本")
        return False
    
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 檢查必要的包
    required_packages = [
        "pytest", "pytest-asyncio", "pytest-cov", 
        "httpx", "fastapi", "pydantic"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少必要的包: {', '.join(missing_packages)}")
        print("請運行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有必要的包都已安裝")
    
    # 檢查測試目錄
    test_dirs = ["tests/unit", "tests/integration", "tests/fixtures"]
    for test_dir in test_dirs:
        if not Path(test_dir).exists():
            print(f"❌ 測試目錄不存在: {test_dir}")
            return False
    
    print("✅ 測試目錄結構正常")
    
    return True


def generate_test_data() -> bool:
    """生成測試數據"""
    print("📊 生成測試數據...")
    
    try:
        from tests.test_data_generator import generate_all_test_data
        result = generate_all_test_data()
        print(f"✅ 測試數據已生成到: {result['output_dir']}")
        return True
    except Exception as e:
        print(f"❌ 生成測試數據失敗: {e}")
        return False


def cleanup_test_artifacts() -> bool:
    """清理測試產物"""
    print("🧹 清理測試產物...")
    
    artifacts = [
        ".coverage",
        "htmlcov/",
        ".pytest_cache/",
        "tests/fixtures/",
        "__pycache__/"
    ]
    
    for artifact in artifacts:
        path = Path(artifact)
        if path.exists():
            if path.is_file():
                path.unlink()
                print(f"🗑️ 刪除文件: {artifact}")
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
                print(f"🗑️ 刪除目錄: {artifact}")
    
    print("✅ 清理完成")
    return True


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="智能文檔轉換RAG系統 - 測試運行器")
    
    # 測試類型選項
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--unit", action="store_true", help="只運行單元測試")
    test_group.add_argument("--integration", action="store_true", help="只運行集成測試")
    test_group.add_argument("--api", action="store_true", help="只運行API測試")
    test_group.add_argument("--parser", action="store_true", help="只運行解析器測試")
    test_group.add_argument("--association", action="store_true", help="只運行關聯分析測試")
    test_group.add_argument("--slow", action="store_true", help="只運行慢速測試")
    test_group.add_argument("--azure", action="store_true", help="只運行Azure OpenAI測試")
    test_group.add_argument("--all", action="store_true", help="運行所有測試")
    test_group.add_argument("--file", type=str, help="運行特定測試文件")
    
    # 通用選項
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細輸出")
    parser.add_argument("--no-coverage", action="store_true", help="禁用覆蓋率報告")
    parser.add_argument("--include-slow", action="store_true", help="在全部測試中包含慢速測試")
    
    # 工具選項
    parser.add_argument("--check-env", action="store_true", help="檢查測試環境")
    parser.add_argument("--generate-data", action="store_true", help="生成測試數據")
    parser.add_argument("--cleanup", action="store_true", help="清理測試產物")
    
    args = parser.parse_args()
    
    # 如果沒有指定任何選項，顯示幫助
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # 工具功能
    if args.check_env:
        success = check_test_environment()
        sys.exit(0 if success else 1)
    
    if args.generate_data:
        success = generate_test_data()
        sys.exit(0 if success else 1)
    
    if args.cleanup:
        success = cleanup_test_artifacts()
        sys.exit(0 if success else 1)
    
    # 測試運行
    print("🧪 智能文檔轉換RAG系統 - 測試開始")
    print(f"📅 開始時間: {__import__('datetime').datetime.now()}")
    
    # 檢查環境
    if not check_test_environment():
        print("❌ 環境檢查失敗，無法運行測試")
        sys.exit(1)
    
    success = False
    coverage = not args.no_coverage
    
    try:
        if args.unit:
            success = run_unit_tests(args.verbose, coverage)
        elif args.integration:
            success = run_integration_tests(args.verbose)
        elif args.api:
            success = run_api_tests(args.verbose)
        elif args.parser:
            success = run_parser_tests(args.verbose)
        elif args.association:
            success = run_association_tests(args.verbose)
        elif args.slow:
            success = run_slow_tests(args.verbose)
        elif args.azure:
            success = run_azure_tests(args.verbose)
        elif args.all:
            success = run_all_tests(args.verbose, coverage, args.include_slow)
        elif args.file:
            success = run_specific_test(args.file, args.verbose)
        else:
            # 默認運行快速測試
            success = run_all_tests(args.verbose, coverage, False)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 測試被用戶中斷")
        sys.exit(1)
    
    # 結果總結
    print(f"\n{'='*60}")
    if success:
        print("🎉 測試完成 - 全部通過!")
    else:
        print("❌ 測試完成 - 有失敗的測試")
    
    print(f"📅 結束時間: {__import__('datetime').datetime.now()}")
    print(f"{'='*60}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
