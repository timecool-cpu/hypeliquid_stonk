#!/bin/bash

# 清理旧文件脚本
# 使用前请确保新结构运行正常！

echo "=================================================="
echo "清理旧文件"
echo "=================================================="
echo ""
echo "⚠️  警告：此操作将删除根目录下的旧文件！"
echo ""
echo "请确保："
echo "  1. 新结构已测试正常"
echo "  2. 已运行 verify_structure.py 验证"
echo "  3. 已备份重要数据"
echo ""
read -p "确认删除旧文件？(输入 YES 继续): " confirm

if [ "$confirm" != "YES" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "开始清理..."

# 核心文件
OLD_FILES=(
    "arbitrage_trader.py"
    "arbitrage_calculator.py"
    "position_manager.py"
    "arbitrage_logger.py"
    "spread_monitor.py"
    "spread_profit_monitor.py"
    "config.py"
    "arbitrage_config.py"
    "utils.py"
    "hip3_trading.py"
)

# 删除文件
for file in "${OLD_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "删除: $file"
        rm "$file"
    else
        echo "跳过: $file (不存在)"
    fi
done

echo ""
echo "✅ 清理完成！"
echo ""
echo "保留的文件："
echo "  - .env (环境变量)"
echo "  - .git (版本控制)"
echo "  - requirements.txt (依赖)"
echo "  - 所有文档和新结构文件"
echo ""
echo "建议运行验证："
echo "  python verify_structure.py"
