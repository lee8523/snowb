# 雪球产品展示系统

一个基于 GitHub 全栈的雪球产品在线展示系统，支持每日自动更新行情数据。

## 📁 项目结构

```
snowball-products/
├── index.html              # 前台展示页面（移动端友好）
├── admin.html              # 管理后台页面
├── data/
│   └── products.json       # 产品数据（自动更新）
├── scripts/
│   └── update_daily.py     # 每日更新脚本
├── .github/
│   └── workflows/
│       └── daily_update.yml  # GitHub Actions 定时任务
└── README.md               # 本文件
```

## 🚀 快速部署

### 1. 创建 GitHub 仓库

```bash
# 在 GitHub 创建新仓库
# 例如：your-username/snowball-products
```

### 2. 推送代码到 GitHub

```bash
cd snowball-products
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/snowball-products.git
git push -u origin main
```

### 3. 启用 GitHub Pages

1. 进入仓库 Settings → Pages
2. Source 选择 `Deploy from a branch`
3. Branch 选择 `main`，文件夹选择 `/ (root)`
4. 点击 Save

### 4. 启用 GitHub Actions

1. 进入仓库 Settings → Actions → General
2. 确保 Actions 已启用
3. 进入 Actions 标签页，确认 `Daily Product Update` workflow 已创建

### 5. 配置访问密码

- 前台密码：`huaxia2026`
- 后台密码：`huaxia2026`

修改密码请编辑：`\"index.html\" 和 `admin.html` 中的 `verifyPassword()` 和 `verifyAdminPassword()` 函数。

## 📱 功能特性

### 前台展示
- ✅ 移动端优先设计（iOS 风格）
- ✅ 产品列表紧凑展示
- ✅ 产品详情弹窗
- ✅ 敲出观察日历
- ✅ 4 色状态标识（已敲出🟢/存续中🔵/已敲入🟡/待期初⚪）
- ✅ 简单密码保护

### 管理后台
- ✅ 产品增删改查
- ✅ 数据统计面板
- ✅ 手动触发更新
- ✅ 密码验证

### 自动更新
- ✅ 每日 16:00 自动更新（北京时间）
- ✅ 获取挂钩标的收盘价
- ✅ 自动计算产品状态
- ✅ 交易日历自动顺延

## 🔧 自定义配置

### 修改更新时间

编辑 `.github/workflows/daily_update.yml`：

```yaml
on:
  schedule:
    # cron 表达式（UTC 时间）
    # 北京时间 16:00 = UTC 08:00
    - cron: '0 8 * * *'
```

### 修改产品类型映射

编辑 `scripts/update_daily.py` 中的 `update_products()` 函数：

```python
# 将"降敲 + 早利"转换为"欧式早利"
if product['type'] == '降敲 + 早利':
    product['type'] = '欧式早利'
```

### 添加新的挂钩标的

编辑 `data/products.json`，在 `products` 数组中添加新产品对象

## 📊 数据说明

### 产品状态
- **待期初**：尚未到期初观察日
- **存续中**：已过期初日，未触发敲出/敲入
- **已敲出**：触发敲出条件，提前终止
- **已敲入**：触发敲入条件，存续至到期

### 敲出观察日规则
- 从第 3 个月开始
- 每月期初对日
- 遇非交易日顺延至下一交易日

## 🛠️ 技术栈

- **前端**：HTML5 + CSS3 + JavaScript（无框架依赖）
- **后端**：Python 3.9 + AKShare（免费行情数据）
- **数据库**：JSON 文件（data/products.json）
- **部署**：GitHub Pages + GitHub Actions
- **定时任务**：GitHub Actions Cron

## ⚠️ 注意事项

1. **数据持久化**：纯静态部署下，管理后台的修改仅在当前会话有效。要实现持久化，需要：
   - 方案 A：使用 GitHub API 直接提交修改
   - 方案 B：搭建后端服务（如 Supabase）

2. **行情数据源**：默认使用 AKShare 免费数据源，如需更稳定数据可切换到：
   - iFinD API（需要账号）
   - Wind API（需要账号）
   - 其他付费数据源

3. **访问控制**：前端密码验证仅为简单防护，不适合高安全场景。

4. **GitHub Actions 限制**：
   - 免费额度：每月 2000 分钟
   - 本系统每天运行 1 次，约占用 30 分钟/月

## 📝 更新日志

- **v1.0** (2026-08-16)
  - 初始版本发布
  - 支持 25 只雪球产品展示
  - 每日自动更新行情
  - 移动端友好界面

## 📞 联系方式

如有问题，请通过 GitHub Issues 反馈。

---

*guest • 2026 • 2026*
