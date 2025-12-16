.PHONY: help install test run run-live clean

help:
	@echo "Hyperliquid TSLA 套利交易系统"
	@echo ""
	@echo "可用命令:"
	@echo "  make install    - 安装依赖"
	@echo "  make test       - 运行测试"
	@echo "  make run        - 运行交易引擎（模拟模式）"
	@echo "  make run-live   - 运行交易引擎（实盘模式）"
	@echo "  make clean      - 清理临时文件"
	@echo ""

install:
	pip install -r requirements.txt

test:
	python3 -m pytest tests/ -v

run:
	python3 scripts/run_trader.py

run-live:
	@echo "⚠️  警告: 即将启动实盘模式！"
	@echo "按 Ctrl+C 取消，或按 Enter 继续..."
	@read dummy
	python3 scripts/run_trader.py --live

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
