# 故障排查指南

## 问题：充值后用量显示为 0

### 原因
API 返回的订单时间是 UTC 时间格式（如 `2026-01-31T01:31:03.000+00:00`），
而代码中的 `start_time` 是本地时间（北京时间）。

之前的代码在比较时间时，只是简单地去掉时区信息进行比较，导致：
- UTC 时间 `01:31:03` 被错误地认为早于本地时间 `08:00:00`
- 充值订单没有被正确识别和计入
- 用量计算公式 `cost = start_balance - current_balance + recharge_total` 出错

### 修复
已修改 `_parse_create_time` 方法，将 UTC 时间转换为北京时间（+8小时）后再进行比较。

### 如何应用修复

1. **更新代码**：确保 Home Assistant 中的集成代码已更新

2. **重新加载集成**：
   - 在 Home Assistant 中进入：设置 → 设备与服务 → Xinao Energy
   - 点击 "..." → 重新加载

3. **如果仍然不正确，需要清除存储数据**：
   
   存储数据位于 Home Assistant 的 `.storage` 目录中，文件名格式为：
   ```
   xinao_energy_data_<entry_id>
   ```
   
   **方法一**：删除存储文件
   ```bash
   # SSH 进入 Home Assistant
   cd /config/.storage
   rm xinao_energy_data_*
   ```
   
   **方法二**：删除并重新添加集成
   - 设置 → 设备与服务 → Xinao Energy → 删除
   - 重新添加集成

4. **重启 Home Assistant**

### 注意事项

- 清除存储数据后，今日/月度的累计数据会从当前时间开始重新计算
- 历史的充值记录会重新从 API 获取并正确处理
