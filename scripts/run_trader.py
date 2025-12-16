#!/usr/bin/env python3
"""
套利交易引擎启动脚本
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.trader import ArbitrageTrader
import argparse


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TSLA FLX vs XYZ 套利交易引擎')
    parser.add_argument('--live', action='store_true', help='实盘模式（默认为模拟模式）')
    args = parser.parse_args()
    
    # 创建交易引擎
    trader = ArbitrageTrader(dry_run=not args.live)
    
    # 运行
    trader.run()


if __name__ == "__main__":
    main()
