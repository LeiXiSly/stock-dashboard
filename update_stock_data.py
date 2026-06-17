#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据自动更新脚本
获取腾讯行情数据并更新 index.html 中的 portfolioData
"""

import re
import json
from datetime import datetime
import urllib.request

# 股票代码列表
STOCKS = {
    '马应龙': {'code': 'sh600993', 'shares': 1000, 'cost': 24.60, 'alarmBuy': 23.00, 'alarmReduce': 25.50, 'alarmStop': 21.00, 'sector': '医药'},
    '普路通': {'code': 'sz002769', 'shares': 2500, 'cost': 8.83, 'alarmBuy': 7.00, 'alarmReduce': 9.50, 'alarmStop': 6.50, 'sector': '供应链'},
    '利欧股份': {'code': 'sz002131', 'shares': 5300, 'cost': 6.53, 'alarmBuy': 4.80, 'alarmReduce': 7.00, 'alarmStop': 4.50, 'sector': '机械/数字营销'},
    '舒华体育': {'code': 'sh605299', 'shares': 7100, 'cost': 17.74, 'alarmBuy': 14.00, 'alarmReduce': 18.50, 'alarmStop': 13.00, 'sector': '体育健身'},
    '比亚迪': {'code': 'sz002594', 'shares': 400, 'cost': 97.14, 'alarmBuy': 85.00, 'alarmReduce': 105.00, 'alarmStop': 80.00, 'sector': '新能源汽车'},
    '科大讯飞': {'code': 'sz002230', 'shares': 1400, 'cost': 65.41, 'alarmBuy': 35.00, 'alarmReduce': 55.00, 'alarmStop': 35.00, 'sector': 'AI/人工智能'}
}

def fetch_stock_data():
    """从腾讯获取股票行情数据"""
    codes = ','.join([info['code'] for info in STOCKS.values()])
    url = f'https://qt.gtimg.cn/q={codes}'
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = response.read().decode('gbk', errors='ignore')
        return data
    except Exception as e:
        print(f"获取行情失败：{e}")
        return None

def parse_stock_info(name, code, raw_data):
    """解析单只股票数据"""
    pattern = rf'v_{code}=".*?"'
    match = re.search(pattern, raw_data)
    if not match:
        return None
    
    content = match.group(0)
    parts = content.split('~')
    
    if len(parts) < 50:
        return None
    
    try:
        price = float(parts[3])
        yesterday_close = float(parts[4])
        open_price = float(parts[5])
        high = float(parts[33]) if parts[33] else price
        low = float(parts[34]) if parts[34] else price
        volume = int(parts[6]) if parts[6] else 0
        turnover = float(parts[38]) if parts[38] else 0
        pe = float(parts[39]) if parts[39] else 0
        
        change = price - yesterday_close
        change_percent = (change / yesterday_close) * 100 if yesterday_close else 0
        
        # 估算日均成交量（简单用当日成交量作为参考）
        avg_volume = int(volume * 1.2)  # 假设日均比当日多 20%
        volume_ratio = volume / avg_volume if avg_volume else 1.0
        
        return {
            'price': price,
            'changePercent': round(change_percent, 2),
            'open': open_price,
            'high': high,
            'low': low,
            'volume': volume,
            'turnover': round(turnover, 2),
            'pe': round(pe, 2),
            'avgVolume5d': avg_volume,
            'volumeRatio': round(volume_ratio, 2)
        }
    except Exception as e:
        print(f"解析{name}数据失败：{e}")
        return None

def generate_analysis(stock_name, data, stock_info):
    """生成简要分析"""
    price = data['price']
    cost = stock_info['cost']
    change = data['changePercent']
    vr = data['volumeRatio']
    
    # 计算盈亏
    pl = (price - cost) * stock_info['shares']
    pl_percent = ((price - cost) / cost) * 100
    
    # 生成分析文本
    if change > 2:
        trend = f"今日大涨{change:.1f}%"
    elif change > 0.5:
        trend = f"今日上涨{change:.1f}%"
    elif change < -2:
        trend = f"今日大跌{change:.1f}%"
    elif change < -0.5:
        trend = f"今日下跌{change:.1f}%"
    else:
        trend = "今日震荡"
    
    # 量能分析
    if vr > 2:
        volume_desc = "显著放量"
    elif vr > 1.5:
        volume_desc = "明显放量"
    elif vr < 0.5:
        volume_desc = "明显缩量"
    else:
        volume_desc = "量能正常"
    
    # 建议
    if price <= stock_info['alarmStop']:
        suggestion = "止损"
        tag = "red"
    elif price >= stock_info['alarmReduce']:
        suggestion = "减仓"
        tag = "orange"
    elif price <= stock_info['alarmBuy']:
        suggestion = "买入"
        tag = "green"
    elif change > 2 and vr > 1.5:
        suggestion = "持有"
        tag = "green"
    elif change < -2 and vr > 1.5:
        suggestion = "减仓"
        tag = "orange"
    else:
        suggestion = "观望"
        tag = "orange"
    
    analysis = f"{stock_name}{trend}，{volume_desc}。"
    if pl_percent > -5:
        analysis += f"接近回本线，耐心持有。"
    elif pl_percent < -30:
        analysis += f"深套中，关注反弹机会。"
    else:
        analysis += f"当前盈亏{pl_percent:.1f}%。"
    
    return {
        'analysis': analysis,
        'suggestion': suggestion,
        'tag': tag,
        'pl': round(pl, 2),
        'plPercent': round(pl_percent, 2)
    }

def update_html(data, stocks_data):
    """更新 HTML 文件"""
    html_path = 'index.html'
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 生成新的 portfolioData
    now = datetime.now()
    update_date = now.strftime('%Y-%m-%d %H:%M')
    
    # 计算汇总数据
    total_market_value = sum(s['price'] * s['shares'] for s in stocks_data.values())
    total_cost = sum(STOCKS[name]['cost'] * STOCKS[name]['shares'] for name in STOCKS)
    total_pl = total_market_value - total_cost
    total_pl_percent = (total_pl / total_cost) * 100
    
    # 构建 stocks 数组
    stocks_json = []
    for name, data_item in stocks_data.items():
        info = STOCKS[name]
        analysis_data = generate_analysis(name, data_item, info)
        
        stock_obj = {
            'code': info['code'][2:],
            'name': name,
            'market': '沪市' if info['code'].startswith('sh') else '深市',
            'shares': info['shares'],
            'price': data_item['price'],
            'cost': info['cost'],
            'changePercent': data_item['changePercent'],
            'open': data_item['open'],
            'high': data_item['high'],
            'low': data_item['low'],
            'pe': data_item['pe'],
            'turnover': data_item['turnover'],
            'pl': analysis_data['pl'],
            'plPercent': analysis_data['plPercent'],
            'analysis': analysis_data['analysis'],
            'suggestion': analysis_data['suggestion'],
            'alarmBuy': info['alarmBuy'],
            'alarmReduce': info['alarmReduce'],
            'alarmStop': info['alarmStop'],
            'sector': info['sector'],
            'tag': analysis_data['tag'],
            'volume': data_item['volume'],
            'avgVolume5d': data_item['avgVolume5d'],
            'volumeRatio': data_item['volumeRatio'],
            'support': info['alarmBuy'],
            'resistance': info['alarmReduce']
        }
        stocks_json.append('    ' + json.dumps(stock_obj, ensure_ascii=False, indent=4))
    
    new_portfolio = f"""const portfolioData = {{
  updateDate: '{update_date}',
  totalAssets: {total_market_value + 1238.88:.2f},
  marketValue: {total_market_value:.2f},
  cash: 1238.88,
  dailyPL: {total_pl:.0f},
  dailyPLPercent: {total_pl_percent:.2f},
  totalPL: {total_pl:.2f},
  totalPLPercent: {total_pl_percent:.2f},
  stocks: [
{chr(10).join(stocks_json)}
  ]
}};"""
    
    # 替换旧数据
    pattern = r'const portfolioData = \{[^}]+\};'
    new_content = re.sub(pattern, new_portfolio, content, flags=re.DOTALL)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 网站数据已更新到 {update_date}")
    print(f"总市值：{total_market_value:.2f}元")
    print(f"总盈亏：{total_pl:.2f}元 ({total_pl_percent:.2f}%)")

def main():
    print("🚀 开始获取股票数据...")
    raw_data = fetch_stock_data()
    
    if not raw_data:
        print("❌ 获取行情失败")
        return
    
    print("📊 解析股票数据...")
    stocks_data = {}
    for name, info in STOCKS.items():
        code = info['code']
        data = parse_stock_info(name, code, raw_data)
        if data:
            stocks_data[name] = data
            print(f"  ✓ {name}: {data['price']}元 ({data['changePercent']:+.2f}%)")
        else:
            print(f"  ✗ {name}: 解析失败")
    
    if len(stocks_data) == len(STOCKS):
        print("\n📝 更新网站数据...")
        update_html(raw_data, stocks_data)
        print("\n✅ 更新完成！")
    else:
        print(f"\n⚠️ 只有{len(stocks_data)}/{len(STOCKS)}只股票数据成功获取")

if __name__ == '__main__':
    main()
