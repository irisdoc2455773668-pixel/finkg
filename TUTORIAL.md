# Finkg 使用教程

> 从零开始，完整掌握 Finkg 金融叙事智能平台的安装、配置和使用。

---

## 目录

- [Part 1：环境准备](#part-1环境准备)
- [Part 2：后端安装与配置](#part-2后端安装与配置)
- [Part 3：前端安装与配置](#part-3前端安装与配置)
- [Part 4：Docker 生产部署](#part-4docker-生产部署)
- [Part 5：配置新闻源](#part-5配置新闻源)
- [Part 6：使用 NLP 引擎](#part-6使用-nlp-引擎)
- [Part 7：市场数据仪表盘](#part-7市场数据仪表盘)
- [Part 8：知识图谱探索](#part-8知识图谱探索)
- [Part 9：自动化报告](#part-9自动化报告)
- [常见问题排查](#常见问题排查)

---

## Part 1：环境准备

在开始使用 Finkg 之前，请确保你的开发环境满足以下要求。

### 1.1 Python 环境

Finkg 后端要求 Python 3.11 或更高版本。

**检查 Python 版本：**

```bash
python --version
# 应输出 Python 3.11.x 或更高
```

**如果未安装或版本过低：**

- **macOS（推荐使用 Homebrew）：**
  ```bash
  brew install python@3.12
  ```

- **Ubuntu/Debian：**
  ```bash
  sudo apt update
  sudo apt install python3.12 python3.12-venv python3-pip
  ```

- **Windows：**
  从 [python.org](https://www.python.org/downloads/) 下载安装包，安装时勾选"Add Python to PATH"。

**配置 Conda 环境（可选但推荐）：**

如果你使用 Conda（如项目遵循的 orangeCai 环境规范），可以创建独立环境：

```bash
conda create -n finkg python=3.12
conda activate finkg
```

### 1.2 Node.js 环境

Finkg 前端要求 Node.js 18 或更高版本。

**检查 Node.js 版本：**

```bash
node --version
# 应输出 v18.x.x 或更高
npm --version
# 应输出 9.x.x 或更高
```

**如果未安装或版本过低：**

- **macOS（推荐使用 Homebrew）：**
  ```bash
  brew install node@20
  ```

- **其他系统：**
  从 [nodejs.org](https://nodejs.org/) 下载 LTS 版本安装包。

### 1.3 Docker 环境（可选）

如果你计划使用 Docker 部署生产环境，需要安装 Docker 和 Docker Compose。

**检查 Docker 安装：**

```bash
docker --version
docker compose version
```

**安装 Docker：**

从 [docker.com](https://www.docker.com/products/docker-desktop/) 下载 Docker Desktop（包含 Docker Compose）。

---

## Part 2：后端安装与配置

### 2.1 获取项目代码

```bash
# 克隆仓库（如果从 GitHub 获取）
git clone https://github.com/your-org/finkg.git
cd finkg

# 或者直接进入已有项目目录
cd /path/to/Finkg
```

### 2.2 配置环境变量

```bash
# 进入后端目录
cd backend

# 复制环境变量模板
cp .env.example .env

# 查看 .env 文件，根据需要修改配置
cat .env
```

默认的 `.env` 文件内容如下：

```bash
# 数据库配置（开发环境使用 SQLite）
DATABASE_URL=sqlite:///finkg.db
DATABASE_URL_ASYNC=sqlite+aiosqlite:///finkg.db

# 服务器配置
HOST=0.0.0.0
PORT=8765
DEBUG=true

# NLP 引擎模式：rule | ml | dify | openai
NLP_ENGINE=rule

# LLM 配置（可选，仅在 NLP_ENGINE=openai/dify 时需要）
DIFY_ENABLED=false
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.deepseek.com/v1

# 代理配置（可选，用于访问受限 API）
FINKG_USE_PROXY=false

# 市场数据更新间隔（秒）
MARKET_UPDATE_INTERVAL=60
```

**环境变量详解：**

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DATABASE_URL` | 否 | `sqlite:///finkg.db` | 数据库连接 URL。生产环境改为 PostgreSQL |
| `DATABASE_URL_ASYNC` | 否 | `sqlite+aiosqlite:///finkg.db` | 异步数据库连接 URL |
| `HOST` | 否 | `0.0.0.0` | 服务器绑定地址 |
| `PORT` | 否 | `8765` | 服务器端口 |
| `DEBUG` | 否 | `true` | 调试模式 |
| `NLP_ENGINE` | 否 | `rule` | NLP 引擎模式 |
| `OPENAI_API_KEY` | 否 | 空 | OpenAI / DeepSeek API 密钥 |
| `OPENAI_BASE_URL` | 否 | `https://api.deepseek.com/v1` | OpenAI 兼容 API 地址 |
| `FINKG_USE_PROXY` | 否 | `false` | 是否使用代理 |

### 2.3 安装 Python 依赖

推荐在虚拟环境中安装依赖：

```bash
# 方式一：使用 venv
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 方式二：使用 Conda
conda activate orangeCai  # 如项目规范所示

# 安装依赖（推荐使用可编辑模式）
pip install -e ".[dev]"
```

`.[dev]` 会安装所有核心依赖和开发依赖（pytest、ruff 等）。

### 2.4 启动后端服务

```bash
# 开发模式（支持热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
```

启动成功后会看到类似输出：

```
INFO:     Uvicorn running on http://0.0.0.0:8765
INFO:     Application startup complete.
INFO:     Database tables created/verified
INFO:     Market data seeded
INFO:     News sources seeded
INFO:     Narrative themes seeded
```

**验证后端运行：**

```bash
# 在另一个终端窗口执行
curl http://localhost:8765/
# 应返回 {"name":"FinKG API","version":"5.0.0","docs":"/docs"}

# 访问 API 文档
open http://localhost:8765/docs
```

### 2.5 运行测试

```bash
# 运行所有测试
cd backend
python -m pytest -v

# 运行特定测试
python -m pytest tests/test_sentiment.py -v

# 带覆盖率报告
python -m pytest --cov=app -v
```

### 2.6 代码检查

```bash
# Ruff 检查
cd backend
ruff check .

# Ruff 自动修复
ruff check --fix .

# Ruff 格式化
ruff format .
```

---

## Part 3：前端安装与配置

### 3.1 安装前端依赖

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 如使用 pnpm（速度更快）
pnpm install
```

### 3.2 启动前端开发服务器

```bash
# 启动（默认端口 5173）
npm run dev
```

启动成功后会看到：

```
VITE v5.x.x  ready in XXX ms
  -> Local:   http://localhost:5173/
```

### 3.3 访问前端界面

打开浏览器访问 http://localhost:5173/

前端默认连接后端 `http://localhost:8765`，可在 `src/api/client.ts` 中修改 API 基础地址。

### 3.4 构建生产版本

```bash
npm run build
# 构建产物在 frontend/dist/ 目录
```

---

## Part 4：Docker 生产部署

### 4.1 使用 Docker Compose 一键部署

在项目根目录执行：

```bash
# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 4.2 服务说明

Docker Compose 会启动以下服务：

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | pgvector/pgvector:pg16 | 5432 | 主数据库（含向量扩展） |
| redis | redis:7-alpine | 6379 | 缓存和消息队列 |
| backend | 本地构建 | 8765 | FastAPI 后端 |
| frontend | 本地构建 | 5173 | Nginx + Vue 前端 |

### 4.3 常用 Docker 命令

```bash
# 停止服务
docker compose down

# 停止并删除数据卷
docker compose down -v

# 重新构建镜像（代码有更改时）
docker compose build

# 重启特定服务
docker compose restart backend

# 查看特定服务日志
docker compose logs -f backend

# 进入容器
docker compose exec backend bash
```

### 4.4 生产环境配置建议

**为 PostgreSQL 设置强密码：** 编辑 `docker-compose.yml`，修改 `POSTGRES_PASSWORD` 为安全密码。

**配置 HTTPS：** 在前面的 Nginx 中配置 SSL 证书，或使用反向代理（如 Nginx Proxy Manager、Caddy）。

**持久化日志：** 配置日志轮转和外部存储。

**资源限制：** 在 Docker Compose 中为每个服务设置 CPU 和内存限制：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## Part 5：配置新闻源

### 5.1 默认新闻源

Finkg 内置了 30+ 中英文金融新闻源配置，存储在项目根目录的 `sources.json` 文件中。启动时，系统会自动将这些源加载到数据库。

### 5.2 查看当前新闻源

通过 API 查看已配置的新闻源：

```bash
curl http://localhost:8765/api/v1/sources
```

### 5.3 手动添加新闻源

**方式一：直接修改 `sources.json` 文件**

```json
{
  "rss_sources": [
    {
      "name": "Reuters Business",
      "url": "https://www.reutersagency.com/feed/",
      "lang": "en",
      "region": "us",
      "cat": "economy",
      "enabled": true
    }
  ],
  "web_sources": [
    {
      "name": "东方财富",
      "url": "https://finance.eastmoney.com/",
      "lang": "zh",
      "region": "cn",
      "cat": "economy",
      "selector": "a.title",
      "base_url": "https://finance.eastmoney.com",
      "encoding": "utf-8",
      "min_len": 12,
      "enabled": true
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 新闻源名称 |
| `url` | String | Feed URL 或页面 URL |
| `lang` | String | 语言代码（zh/en） |
| `region` | String | 地区代码（cn/us/eu/jp/...) |
| `cat` | String | 分类（economy/politics/markets/tech） |
| `enabled` | Boolean | 是否启用 |
| `selector` | String | Web 源的 CSS 选择器 |
| `base_url` | String | 相对链接的基础 URL |
| `encoding` | String | 页面编码 |
| `min_len` | Integer | 最小正文长度 |
| `political_leaning` | String | 政治倾向（用于分析偏差） |
| `reliability` | Float | 可信度评分（0-1） |

**方式二：通过 API 动态添加**

```bash
curl -X POST http://localhost:8765/api/v1/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Financial Times",
    "url": "https://www.ft.com/?format=rss",
    "source_type": "rss",
    "language": "en",
    "region": "uk",
    "category": "economy"
  }'
```

### 5.4 手动触发新闻抓取

```bash
# 触发抓取所有启用源
curl -X POST http://localhost:8765/api/v1/news/fetch

# 查看抓取结果
curl http://localhost:8765/api/v1/news?limit=10
```

### 5.5 自定义抓取调度

编辑后端的配置文件或通过设置 API 调整抓取间隔：

```bash
# 查看当前调度状态
curl http://localhost:8765/api/v1/pipeline/status
```

---

## Part 6：使用 NLP 引擎

Finkg 的 NLP 引擎提供三种模式，从轻量到深度，可根据使用场景灵活切换。

### 6.1 规则引擎（默认）

规则引擎无需外部依赖，启动即可使用，适合快速原型和实时分析。

**配置方式：** 在 `.env` 中设置 `NLP_ENGINE=rule`

**功能特点：**
- 中文分词（jieba）
- 金融情感词典分析（3000+ 正面词，5000+ 负面词）
- 否定词反转和程度副词加权
- 基础实体提取（基于词性标注和正则）

**测试情感分析：**

```bash
curl -X POST http://localhost:8765/api/v1/analysis/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "美联储加息50个基点，市场信心受挫，科技股大幅下跌。"}'
```

预期返回：

```json
{
  "score": -0.67,
  "label": "negative",
  "details": {
    "positive_words": [],
    "negative_words": ["受挫", "下跌"],
    "compound_score": -0.67
  }
}
```

### 6.2 ML 引擎

ML 引擎使用 scikit-learn 进行更精细的文本分析。

**配置方式：** 在 `.env` 中设置 `NLP_ENGINE=ml`

**功能特点：**
- TF-IDF 向量化文本表示
- LDA 主题模型自动发现隐藏主题
- NMF 主题模型（LDA 的替代方案）
- 基于上下文的实体分类

**使用主题建模：**

```bash
curl -X POST http://localhost:8765/api/v1/analysis/topics \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "美联储宣布加息50个基点应对通胀压力",
      "科技股暴跌，纳斯达克指数下跌超过3%",
      "央行下调LPR利率，房地产板块迎来利好",
      "国际油价突破85美元，能源股集体上涨"
    ],
    "num_topics": 2
  }'
```

### 6.3 LLM 引擎（DeepSeek / OpenAI）

LLM 引擎提供最深入的语义理解，基于大语言模型进行情感分析、实体提取和报告生成。

**配置方式：**

```bash
# .env 文件
NLP_ENGINE=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

**为什么要将 DeepSeek 作为默认 LLM：**
- DeepSeek API 兼容 OpenAI SDK，切换成本为零
- DeepSeek 在中文金融文本理解方面表现优异
- 成本远低于 OpenAI

**如果使用 OpenAI：**

```bash
OPENAI_API_KEY=sk-your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

**如果使用 Dify 平台：**

```bash
NLP_ENGINE=dify
DIFY_ENABLED=true
# 同时需要设置 DIFY_API_KEY 和 DIFY_BASE_URL（在代码中配置）
```

**LLM 情感分析示例：**

```bash
curl -X POST http://localhost:8765/api/v1/analysis/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "央行今日宣布降准0.5个百分点，释放长期资金约1万亿元，此举将有效降低企业融资成本，提振市场信心。"}'
```

LLM 引擎会返回更细致的分析结果，包括情感依据和上下文解释。

### 6.4 引擎切换对比

| 特性 | 规则引擎 | ML 引擎 | LLM 引擎 |
|------|---------|---------|---------|
| 启动速度 | 即时 | 需要训练 | 需 API 调用 |
| 外部依赖 | 无 | scikit-learn | API Key |
| 分析速度 | 毫秒级 | 秒级 | 秒到分钟级 |
| 中文支持 | 好 | 中 | 优 |
| 语义理解 | 差（关键词） | 中 | 优 |
| 上下文感知 | 无 | 有限 | 强 |
| 运行成本 | 零 | 低 | API 费用 |
| 适用场景 | 实时分析 | 批量分析 | 深度分析 |

### 6.5 实体提取

```bash
curl -X POST http://localhost:8765/api/v1/analysis/entities \
  -H "Content-Type: application/json" \
  -d '{"text": "华为与特斯拉宣布在自动驾驶领域达成战略合作，双方将共同投资20亿美元在上海建立研发中心。"}'
```

返回结果包含实体的名称、类型、位置等信息。

---

## Part 7：市场数据仪表盘

### 7.1 查看市场数据

```bash
# 获取所有市场指标
curl http://localhost:8765/api/v1/market/indices
```

### 7.2 查看单个指标

```bash
# 查看标普500指数
curl http://localhost:8765/api/v1/market/indices/SPX
```

### 7.3 数据类别

Finkg 追踪 34 个全球关键市场指标，分为以下类别：

1. **股票指数**：SPX、NDX、DAX、FTSE、N225、HSI、SHCOMP、A50
2. **外汇**：EURUSD、USDJPY、GBPUSD、USDCNY、DXY
3. **商品**：BRENT、NATGAS、GOLD、SILVER、COPPER
4. **加密货币**：BTC、ETH
5. **债券**：US2Y、US10Y、US3M
6. **利率**：FEDFUNDS、CN_LPR1Y
7. **通胀**：US_CPI、US_PPI、CN_CPI、CN_PPI
8. **就业**：US_UNEMP
9. **GDP**：US_GDP、CN_GDP
10. **PMI**：CN_PMI
11. **风险**：VIX

### 7.4 市场数据与叙事的关联

Finkg 的一大特色是将市场数据与叙事分析关联。当某个叙事被大量报道时，可以观察相关市场指标的走势变化，从而验证叙事对市场的影响。

---

## Part 8：知识图谱探索

### 8.1 知识图谱简介

Finkg 的知识图谱将新闻中提取的实体（人物、组织、地点、金融工具等）和它们之间的关系（合作、竞争、投资、收购等）组织为图结构，支持交互式探索。

### 8.2 查询图谱

```bash
# 获取所有实体
curl http://localhost:8765/api/v1/graph/entities

# 获取实体关系
curl http://localhost:8765/api/v1/graph/relations

# 按实体名称查询
curl "http://localhost:8765/api/v1/graph/query?entity=华为"

# 按关系类型查询
curl "http://localhost:8765/api/v1/graph/query?relation_type=合作"
```

### 8.3 前端图谱交互

通过前端知识图谱页面（GraphView），你可以：

- **拖拽节点**：自由排列实体节点
- **缩放**：滚轮缩放查看整体或细节
- **点击节点**：查看实体详情和相关新闻
- **悬停连线**：查看关系类型和权重
- **搜索实体**：快速定位特定实体

### 8.4 实体影响力分析

Finkg 基于图论计算实体的中心性指标，帮助识别叙事网络中的关键实体：

- **度中心性**：与该实体直接相连的其他实体数量
- **介数中心性**：该实体位于其他实体之间最短路径上的频率
- **接近中心性**：该实体到所有其他实体的平均距离的倒数

高中心性实体通常是叙事传播的关键节点。

---

## Part 9：自动化报告

### 9.1 触发报告生成

```bash
# 生成默认报告
curl -X POST http://localhost:8765/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "daily_briefing",
    "date": "2026-07-27"
  }'
```

**报告类型说明：**

| 类型 | 说明 | 内容 |
|------|------|------|
| `daily_briefing` | 每日简报 | 当日热点新闻、情感趋势、关键数据 |
| `narrative_tracking` | 叙事追踪 | 指定叙事的演变脉络和影响分析 |
| `market_review` | 市场综述 | 结合市场数据和叙事的综合分析 |
| `research` | 专题研究 | 特定主题的深度分析报告 |

### 9.2 查看已生成报告

```bash
# 获取报告列表
curl http://localhost:8765/api/v1/reports

# 获取报告详情
curl http://localhost:8765/api/v1/reports/1
```

### 9.3 报告内容示例

Finkg 生成的报告包含以下典型内容：

1. **摘要**：报告的核心发现概览
2. **热点叙事**：当前最活跃的叙事主题及其强度
3. **情感趋势**：市场整体情感变化（图表）
4. **关键实体**：被提及最多的实体及其关系
5. **市场关联**：叙事强度与市场指标的关联分析
6. **结论与展望**：基于当前叙事趋势的未来展望

### 9.4 LLM 报告定制

当使用 LLM 引擎时，可以通过调整提示词模板来定制报告风格和关注点。

---

## 常见问题排查

### Q1：后端启动报错 "sqlite3.OperationalError: unable to open database file"

**原因：** SQLite 数据库文件所在的目录没有写入权限。

**解决：**
```bash
# 确保 backend 目录可写
chmod 755 backend/
# 或者指定数据库文件路径
export DATABASE_URL=sqlite:////tmp/finkg.db
```

### Q2：前端无法连接到后端 API

**原因：** 跨域配置不正确或后端未启动。

**解决：**
1. 确保后端已启动：`curl http://localhost:8765/`
2. 检查 CORS 配置：后端默认允许 `localhost:5173`
3. 检查前端 `src/api/client.ts` 中的 `baseURL` 配置

### Q3：RSS 新闻抓取返回空结果

**原因：**
- 新闻源 URL 已过期
- 网络问题无法访问 RSS 源
- 需要使用代理

**解决：**
```bash
# 启用代理
export FINKG_USE_PROXY=true
# 配置 SOCKS5 代理（在 .env 中或环境变量中设置）
export HTTP_PROXY=socks5://127.0.0.1:7890
export HTTPS_PROXY=socks5://127.0.0.1:7890
```

### Q4：NLP 引擎切换后不生效

**原因：** 环境变量更改后需要重启后端服务。

**解决：**
```bash
# 停止后端服务（Ctrl+C），然后重新启动
uvicorn app.main:app --reload
```

### Q5：Docker Compose 启动时 PostgreSQL 连接失败

**原因：** PostgreSQL 服务尚未就绪，后端启动过早。

**解决：** Docker Compose 已配置 `depends_on: condition: service_healthy`，但首次启动可能需要等待数据库初始化。耐心等待 30-60 秒后重试：

```bash
docker compose logs -f backend
```

### Q6：LLM API 调用返回 401 错误

**原因：** API Key 无效或未配置。

**解决：**
1. 检查 `.env` 中的 `OPENAI_API_KEY` 是否正确
2. 检查 API Key 是否还有余额
3. 验证 API Base URL 是否正确（DeepSeek：`https://api.deepseek.com/v1`）

### Q7：jieba 分词不准确

**原因：** jieba 默认词典可能不包含金融领域的专有词汇。

**解决：** 可以通过添加自定义词典来改进分词效果。编辑相关配置文件，将金融专有词汇添加到自定义词典中。

### Q8：scikit-learn 依赖安装失败

**原因：** 在某些系统上，scikit-learn 需要编译原生代码。

**解决：**
```bash
# 确保安装了构建工具
# macOS
xcode-select --install
# Ubuntu
sudo apt install build-essential

# 安装 numpy 后再安装 scikit-learn
pip install numpy
pip install scikit-learn
```

### Q9：前端页面显示空白或报错

**原因：**
- TypeScript 类型错误
- Vue 组件编译错误
- API 请求失败

**解决：**
1. 打开浏览器开发者工具（F12）查看控制台错误
2. 运行类型检查：`npm run type-check`
3. 清除缓存：`rm -rf frontend/node_modules/.vite`
4. 重新安装依赖：`rm -rf frontend/node_modules && npm install`

### Q10：如何重置数据库？

**开发环境（SQLite）：**

```bash
# 删除 SQLite 数据库文件
rm backend/finkg.db
# 重启后端，会自动重新创建并填充种子数据
uvicorn app.main:app --reload
```

**生产环境（PostgreSQL）：**

```bash
# 使用 Docker 清除数据卷
docker compose down -v
docker compose up -d
```

> **注意：** 重置数据库会丢失所有已抓取的新闻、分析结果和报告数据，请谨慎操作。
