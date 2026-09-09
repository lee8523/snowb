# 雪球产品展示系统

基于 GitHub 全栈的雪球产品展示系统：纯静态前端 + Python 更新脚本，用 GitHub 仓库本身存储数据，GitHub Pages 部署，GitHub Actions 每日自动更新行情与产品状态。

## 页面结构

| 页面 | 职责 |
|---|---|
| `index.html` | 登录页，校验用户名/密码后跳转展示页 |
| `products.html` | 产品展示页（列表、详情弹窗、敲出观察日历、四色状态） |
| `admin.html` | 管理后台（产品增删改查预览、统计；保存尚未接持久化，仅本地预览） |

## 数据流

```
vendor/market-data（新浪/腾讯/东财三源行情，git 子模块）
        │
        ▼
updater.py（每日更新价格、判定敲出、计算状态）
        │
        ▼
data/products.json ── CI 自动 commit 回 main ── 前端 fetch 展示
```

## 核心文件

- `updater.py` — 数据更新脚本：
  - `python updater.py initial` — 按期初观察日收盘价回填期初价、重算敲入价（一次性）
  - `python updater.py daily` — 每日更新：当前价、观察日敲出判定、四态状态、距下次观察日天数
  - 行情获取失败自动重试（共 3 次，间隔 3 分钟）
- `trading_calendar.py` — 交易日历（**节假日唯一真相源**）：内置 2026-2030 年国务院放假安排，提供 `is_trading_day` / `next_trading_day`；如需 JSON 日历可调用 `save_calendar()` 重新生成
- `import_from_excel.py` — 从 Excel 导入产品数据到 `data/products.json`（依赖 openpyxl，Excel 列结构见文件头注释）
- `tools/add_user.py` — 本地添加/管理登录用户（git 忽略，不入库）
- `tests/test_updater.py` — 单元测试（观察日历生成、四态计算、敲出价、交易日接口）
- `.github/workflows/daily-update.yml` — 每日定时任务（UTC 08:00 = 北京 16:00），跑 `updater.py daily` 后自动提交 `data/products.json` 回 main，支持在 Actions 页面手动触发

## 用户认证

登录校验基于 `data/users.json`（用户名 + SHA-256 密码哈希，前端比对）。添加用户：

```bash
python tools/add_user.py
```

## 本地运行

```bash
git clone --recurse-submodules <仓库地址>
pip install requests        # 行情模块依赖
python updater.py daily     # 手动跑一次每日更新
python -m unittest discover -s tests -v   # 运行单元测试
```

注意：本地运行 `updater.py` 会直接修改 `data/products.json` 并在 `data/backup/` 生成备份（仅保留最近 30 份，已 git 忽略）。

## 部署

1. GitHub Pages：Settings → Pages → Deploy from a branch → `main` / root
2. GitHub Actions：默认 GITHUB_TOKEN 即可，无需配置 secrets
3. 更换仓库名/所有者时，需同步修改 `index.html` 中的 `GITHUB_OWNER` / `GITHUB_REPO` 常量

## 维护提示

- **交易日历年度更新**：`trading_calendar.py` 中 2027 年及以后的节假日为预测值，每年 11 月国务院公布次年安排后需手动更新 `HOLIDAYS` 字典，改完跑一遍单元测试验证
- **管理后台持久化**：当前 admin 页面的保存仅为本地预览，接入真实持久化需要配置 GitHub API Token（待后续实现）
- **产品状态规则**：待期初（未到期初日）/ 已敲出（观察日收盘价 ≥ 当月敲出价）/ 已敲入（期末观察日收盘价 ≤ 敲入价）/ 存续中

## 技术栈

- 前端：HTML5 + CSS3 + 原生 JavaScript（无框架、无构建）
- 后端脚本：Python 3.9+
- 行情数据：`vendor/market-data` 子模块（新浪/腾讯/东方财富多源 fallback）
- 存储：仓库内 JSON 文件
- 部署：GitHub Pages + GitHub Actions
