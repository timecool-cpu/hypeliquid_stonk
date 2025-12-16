"""
测试直接调用 API 来获取 xyz:TSLA 的订单簿数据
"""
import requests
import json

# 直接使用 HTTP 请求测试
url = "https://api.hyperliquid.xyz/info"

# 尝试获取 xyz:TSLA 的 L2 订单簿
payload = {
    "type": "l2Book",
    "coin": "xyz:TSLA"
}

print(f"请求 payload: {json.dumps(payload, indent=2)}\n")

response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})

print(f"响应状态码: {response.status_code}\n")
print(f"响应内容:\n{json.dumps(response.json(), indent=2)}")
