# 新奥燃气能源分析 Home Assistant 集成

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/forrestsocool/xinao_energy.svg)](https://github.com/forrestsocool/xinao_energy/releases)
[![License](https://img.shields.io/github/license/forrestsocool/xinao_energy.svg)](LICENSE)

这个集成允许你在 Home Assistant 中监控新奥燃气的用气量和费用。

## 功能特性

- 实时账户余额监控
- 当月用气量和费用跟踪
- 每日用量历史记录和统计
- 阶梯气价信息显示
- 欠费金额追踪
- 可配置的更新间隔
- 完整的中英文语言支持

## 安装方式

### 通过 HACS 安装（推荐）

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=forrestsocool&repository=xinao_energy&category=integration)

1. 点击上方按钮，或在 HACS 中添加自定义存储库
2. 搜索 "Xinao Energy Analysis"
3. 点击安装
4. 重启 Home Assistant
5. 前往 **配置 → 设备与服务 → 添加集成**
6. 搜索 "Xinao Energy Analysis"

### 手动安装

1. 下载 `custom_components/xinao_energy` 文件夹
2. 复制到你的 Home Assistant `custom_components` 目录
3. 重启 Home Assistant
4. 前往 **配置 → 设备与服务**
5. 点击 "+ 添加集成" 按钮
6. 搜索 "Xinao Energy Analysis"

## 配置说明

在设置过程中，你需要提供以下信息：

- **Token（令牌）**: 从新奥燃气 API 获取的认证令牌
- **Payment Number（缴费号）**: 你的燃气缴费账号
- **Company Code（公司代码）**: 公司代码（默认: 0081）
- **Update Interval（更新间隔）**: 数据更新频率，单位为分钟（默认: 30）

### 如何获取 Token

1. 使用抓包工具（如 Charles、Fiddler）监听新奥燃气微信小程序的请求
2. 在请求头中找到 `token` 字段
3. 复制该 token 值用于配置

## 传感器说明

本集成会创建以下传感器：

### 基础传感器

1. **账户余额** (`sensor.xinao_balance`)
   - 当前账户余额（人民币）
   - 属性：上月余额（如果可用）

2. **欠费金额** (`sensor.xinao_arrears_amount`)
   - 未缴费用金额（人民币）

3. **当月用量** (`sensor.xinao_current_month_usage`)
   - 当前月份的用气量（立方米）
   - 属性：阶梯气价周期说明

4. **当月费用** (`sensor.xinao_current_month_cost`)
   - 当前月份的总费用（人民币）
   - 属性：预估费用（如果可用）、阶梯气价周期说明

5. **总用气量** (`sensor.xinao_total_gas_count`)
   - 累计总用气量（立方米）

6. **可用天数** (`sensor.xinao_available_days`)
   - 基于当前余额预估的可用天数

### 高级传感器

7. **每日用量** (`sensor.xinao_daily_usage`)
   - 今日用气量（立方米）
   - 属性：
     - `history`: 每日用量记录列表
     - `total_days`: 有数据的天数
     - `average_usage`: 平均每日用量
     - `max_usage`: 最大每日用量
     - `min_usage`: 最小每日用量
     - `total_usage`: 所有每日用量总和

8. **阶梯气价** (`sensor.xinao_ladder_price`)
   - 当前适用的气价档位（元/立方米）
   - 属性：
     - `ladder_tiers`: 所有价格档位列表
     - `total_tiers`: 价格档位数量
     - `cycle_description`: 计价周期说明

## 自动化示例

### 余额不足提醒

```yaml
automation:
  - alias: "燃气余额不足提醒"
    trigger:
      - platform: numeric_state
        entity_id: sensor.xinao_balance
        below: 100
    action:
      - service: notify.mobile_app
        data:
          message: "燃气余额不足：{{ states('sensor.xinao_balance') }} 元"
```

### 高用量提醒

```yaml
automation:
  - alias: "燃气用量过高提醒"
    trigger:
      - platform: numeric_state
        entity_id: sensor.xinao_daily_usage
        above: 10
    action:
      - service: notify.mobile_app
        data:
          message: "今日燃气用量较高：{{ states('sensor.xinao_daily_usage') }} 立方米"
```

### 每月费用统计通知

```yaml
automation:
  - alias: "每月燃气费用统计"
    trigger:
      - platform: time
        at: "09:00:00"
      - platform: template
        value_template: "{{ now().day == 1 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "上月燃气费用统计"
          message: >
            上月用量：{{ states('sensor.xinao_current_month_usage') }} m³
            上月费用：{{ states('sensor.xinao_current_month_cost') }} 元
            当前余额：{{ states('sensor.xinao_balance') }} 元
```

## 仪表板卡片示例

### 基础卡片

```yaml
type: entities
title: 新奥燃气
entities:
  - entity: sensor.xinao_balance
    name: 账户余额
  - entity: sensor.xinao_current_month_usage
    name: 本月用量
  - entity: sensor.xinao_current_month_cost
    name: 本月费用
  - entity: sensor.xinao_daily_usage
    name: 今日用量
  - entity: sensor.xinao_ladder_price
    name: 当前气价
```

### 统计卡片

```yaml
type: vertical-stack
cards:
  - type: glance
    title: 新奥燃气概览
    entities:
      - entity: sensor.xinao_balance
        name: 余额
      - entity: sensor.xinao_current_month_usage
        name: 本月用量
      - entity: sensor.xinao_current_month_cost
        name: 本月费用

  - type: statistics-graph
    title: 每日用量趋势
    entities:
      - sensor.xinao_daily_usage
    stat_types:
      - mean
      - min
      - max
    period: week
```

### Mushroom 卡片（需要安装 Mushroom 卡片）

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: 新奥燃气

  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: sensor.xinao_balance
        name: 余额
        icon: mdi:cash

      - type: custom:mushroom-entity-card
        entity: sensor.xinao_current_month_usage
        name: 本月用量
        icon: mdi:fire

  - type: custom:mushroom-entity-card
    entity: sensor.xinao_daily_usage
    name: 今日用量
    icon: mdi:calendar-today
    tap_action:
      action: more-info
```

## API 信息

本集成使用新奥燃气微信小程序 API：
- 接口地址: `https://wechatapp.ecej.com/livingpay/v3/xcx/electricity/getEnergyAnalysis.json`
- 认证方式: 基于 Token 的认证，带动态 appKey 生成

## 常见问题

### 无法连接错误
- 验证你的 token 是否有效且未过期
- 检查缴费号是否正确
- 确保 Home Assistant 可以访问互联网

### 无效认证错误
- 你的 token 可能已过期
- 尝试从新奥燃气应用重新获取 token

### 没有返回数据
- 缴费号可能没有最近的用量数据
- 检查公司代码是否适用于你的地区

### Token 过期了怎么办？
1. 前往 **配置 → 设备与服务**
2. 找到 "Xinao Energy Analysis" 集成
3. 点击 "配置"
4. 删除并重新添加集成，输入新的 token

## 技术支持

如有问题和功能建议，请访问 [GitHub 仓库](https://github.com/forrestsocool/xinao_energy)提交 Issue。

## 贡献

欢迎提交 Pull Request 来改进这个集成！

## 许可证

MIT License

## 致谢

感谢所有为这个项目做出贡献的开发者！
