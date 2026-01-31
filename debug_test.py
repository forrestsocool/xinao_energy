"""Test script to verify the UTC timezone fix works correctly."""
import hashlib
import json
from datetime import datetime, timedelta

import requests

# Configuration - from user
TOKEN = "4c97230346904b65a5650cbdbee04fe1"
DEVICE_ID = "803984"
CITY_ID = "62"

# API URLs
API_URL = "https://iot.ecej.com/app/device/model/detail/v1"
ORDER_LIST_URL = "https://oc.ecej.com/v1/order/bizOrderList"
API_SECRET = "8796135e9f8349d998345f9f13d8bd95"


def generate_app_key():
    """Generate appKey with timestamp and MD5 signature."""
    now = datetime.now()
    time_str = now.strftime("%Y%m%d%H%M%S")
    sign_str = time_str + API_SECRET
    md5_hash = hashlib.md5(sign_str.encode("utf-8")).hexdigest()
    app_key = time_str + md5_hash.upper()
    return app_key


def parse_create_time(order: dict) -> datetime | None:
    """Parse createTime field - the fixed version."""
    create_time_str = order.get("createTime", "")
    if create_time_str:
        try:
            clean_str = create_time_str
            if "." in clean_str:
                parts = clean_str.split(".")
                base = parts[0]
                tz_part = ""
                if "+" in parts[1]:
                    tz_part = "+" + parts[1].split("+")[1]
                elif "-" in parts[1]:
                    tz_part = "-" + parts[1].split("-")[1]
                clean_str = base + tz_part
            
            if "+00:00" in clean_str or "Z" in clean_str:
                clean_str = clean_str.replace("Z", "+00:00")
                dt_utc = datetime.fromisoformat(clean_str)
                dt_local = dt_utc.replace(tzinfo=None) + timedelta(hours=8)
                return dt_local
            else:
                dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S")
                return dt
        except ValueError as e:
            print(f"Failed to parse createTime '{create_time_str}': {e}")
    return None


def get_gas_data():
    """Get gas data."""
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://iot.ecej.com",
        "withCredentials": "true",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15",
        "Authorization": f"Bearer {TOKEN}",
        "Host": "iot.ecej.com",
        "Accept": "application/json, text/plain, */*",
    }
    body = {
        "deviceId": DEVICE_ID,
        "deviceType": "3",
        "appKey": generate_app_key(),
    }
    response = requests.post(API_URL, headers=headers, json=body, timeout=10)
    return response.json()


def get_order_list():
    """Get order list."""
    headers = {
        "Host": "oc.ecej.com",
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "ECEJ/6.5.9 (iPhone; iOS 14.8; Scale/2.00)",
        "platform": "ios",
        "cityId": CITY_ID,
    }
    data = {
        "appKey": generate_app_key(),
        "orderStatus": "0",
        "pageNum": "1",
        "pageSize": "10",
        "token": TOKEN,
        "type": "2",
        "version": "1",
    }
    response = requests.post(ORDER_LIST_URL, headers=headers, data=data, timeout=10)
    return response.json()


def simulate_calculation():
    """Simulate the calculation logic."""
    print("=" * 60)
    print("Testing API calls and calculation logic")
    print("=" * 60)
    
    # Get gas data
    print("\n1. Fetching gas data...")
    gas_result = get_gas_data()
    if gas_result.get("code") != 200:
        print(f"   ERROR: {gas_result}")
        return
    
    data = gas_result.get("data", {})
    balance = data.get("balance", 0)
    gas_price = data.get("gasPrice", 0)
    print(f"   Balance: {balance}")
    print(f"   Gas Price: {gas_price}")
    
    # Get orders
    print("\n2. Fetching order list...")
    order_result = get_order_list()
    if order_result.get("resultCode") != 200:
        print(f"   ERROR: {order_result}")
        return
    
    orders = order_result.get("data", [])
    completed_orders = [o for o in orders if o.get("orderStat") == 3]
    print(f"   Found {len(completed_orders)} completed orders")
    
    # Parse order times
    print("\n3. Testing order time parsing (UTC -> Local conversion)...")
    for order in completed_orders[:3]:  # First 3 orders
        order_id = order.get("orderId")
        create_time_raw = order.get("createTime")
        amount = order.get("numDesc")
        
        parsed_time = parse_create_time(order)
        
        print(f"\n   Order {order_id}:")
        print(f"     Amount: {amount} CNY")
        print(f"     Raw createTime (UTC): {create_time_raw}")
        print(f"     Parsed local time: {parsed_time}")
        if parsed_time:
            print(f"     Local time str: {parsed_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Simulate monthly calculation
    print("\n4. Simulating monthly calculation...")
    
    # Assume start of month
    month_start = datetime(2026, 1, 1, 0, 0, 0)
    print(f"   Month start: {month_start}")
    
    # Find all orders this month
    monthly_recharge = 0.0
    monthly_orders = []
    for order in completed_orders:
        order_time = parse_create_time(order)
        if order_time and order_time >= month_start:
            amount = float(order.get("numDesc", "0"))
            monthly_recharge += amount
            monthly_orders.append({
                "id": order.get("orderId"),
                "amount": amount,
                "time": order_time.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    print(f"   Orders this month: {len(monthly_orders)}")
    for o in monthly_orders:
        print(f"     - {o['time']}: {o['amount']} CNY (ID: {o['id']})")
    print(f"   Total monthly recharge: {monthly_recharge} CNY")
    
    # Calculate usage
    # Assuming start_balance was recorded at month start
    # For demo, let's use a hypothetical start balance
    hypothetical_start_balance = 800.0  # You'll need the actual value from storage
    
    monthly_cost = hypothetical_start_balance - balance + monthly_recharge
    monthly_usage = monthly_cost / gas_price if gas_price > 0 else 0
    
    print(f"\n5. Calculation example (hypothetical start_balance={hypothetical_start_balance}):")
    print(f"   monthly_cost = start_balance - current_balance + recharge_total")
    print(f"   monthly_cost = {hypothetical_start_balance} - {balance} + {monthly_recharge}")
    print(f"   monthly_cost = {monthly_cost:.2f} CNY")
    print(f"   monthly_usage = {monthly_cost:.2f} / {gas_price} = {monthly_usage:.3f} m³")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    simulate_calculation()
