# Finkg — 金融叙事智能平台

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.5%2B-4FC08D?style=flat-square&logo=vue.js" alt="Vue 3">
  <img src="https://img.shields.io/badge/TypeScript-5.5%2B-3178C6?style=flat-square&logo=typescript" alt="TypeScript">
  <img src="https://img.shields.io/badge/NLP-Sentiment%20%7C%20Entity%20%7C%20Topic-FF6F00?style=flat-square" alt="NLP">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License">
</p>

<p align="center">
  <strong>Financial Narrative Intelligence Platform</strong> —— 融合金融、自然语言处理与知识图谱的叙事智能分析系统
</p>

---

## 目录

- [项目概述](#项目概述)
- [核心功能](#核心功能)
- [架构概览](#架构概览)
- [快速开始](#快速开始)
  - [环境要求](#环境要求)
  - [后端启动](#后端启动)
  - [前端启动](#前端启动)
  - [Docker 部署](#docker-部署)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [API 端点概览](#api-端点概览)
- [联系我们](#联系我们)
- [许可证](#许可证)

---

## 项目概述

Finkg（FinKG 5.0）是一个开源的金融叙事智能平台，旨在通过自然语言处理、知识图谱和市场数据集成，帮助分析师、投资者和研究人员从海量金融新闻中提取叙事脉络，量化市场情绪，发现隐藏的关联关系。

**核心理念：** 金融市场的波动不仅由基本面驱动，更受市场叙事（Narratives）的深刻影响。Finkg 通过系统性追踪、分析和量化金融叙事，为用户提供超越传统技术面和基本面分析的增量洞察。

### 应用场景

- **量化研究员：** 将叙事信号纳入量化模型，构建替代数据因子
- **宏观分析师：** 追踪全球主要经济体的政策叙事演变
- **行业研究员：** 监控特定行业的舆论风向和情绪变化
- **风险管理：** 早期识别地缘政治、监管政策等叙事风险
- **舆情监控：** 实时追踪社交媒体和新闻中的热点叙事

---

## 核心功能

### 1. 多源新闻聚合
- 支持 RSS Feed 和 Web 页面抓取
- 内置 30+ 中英文金融新闻源配置
- 定时调度与增量抓取，自动去重
- 可自定义新闻源和抓取策略

### 2. 实时情感分析
- 三层 NLP 引擎架构：规则引擎 → 机器学习 → 大语言模型
- 金融领域专用情感词典（基于 SentiWordNet + 金融语料）
- 支持中英文双语情感分析
- 细粒度情感分类：正面 / 负面 / 中性 / 混合

### 3. 实体提取与链接
- 人名、组织、地点、金融工具等多类型实体识别
- 实体共现分析与关联度计算
- 实体-叙事关联映射

### 4. 主题建模与叙事追踪
- LDA / NMF 主题模型自动发现隐藏主题
- 叙事生命周期追踪（兴起 → 高潮 → 消退）
- 叙事强度与传播度量化

### 5. 知识图谱
- 实体-关系存储（基于 SQLite/PostgreSQL）
- 叙事传播路径可视化
- 实体影响力计算
- 交互式图谱探索（前端 ECharts 渲染）

### 6. 市场数据仪表盘
- 34+ 全球市场指标实时追踪
- 涵盖股票、外汇、商品、债券、利率、通胀、就业等类别
- 自动数据更新与可视化

### 7. 自动化报告
- LLM 驱动的智能报告生成
- 支持多维度报告：每日舆情、叙事追踪、市场综述
- 可配置的报告模板与输出格式

---

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    用户界面 (Vue 3)                       │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐ │
│  │ 仪表盘   │ │ 新闻浏览 │ │ 图谱  │ │ 报告 & 设置  │ │
│  └──────────┘ └──────────┘ └────────┘ └──────────────┘ │
│          Naive UI 组件库 + ECharts 可视化                │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI API 层 (v1)                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │ 新闻 │ │ 分析 │ │ 市场 │ │ 图谱 │ │ 报告 │ │ 管道 │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │
└──────┬──────────────────────────────────┬───────────────┘
       │                                  │
┌──────▼──────────┐            ┌─────────▼──────────────┐
│   NLP 引擎       │            │   数据服务层             │
│  ┌────────────┐  │            │  ┌──────────────────┐  │
│  │ 规则引擎   │  │            │  │ RSS 爬虫调度器   │  │
│  │ (jieba +   │  │            │  │ APScheduler      │  │
│  │  词典)     │  │            │  └──────────────────┘  │
│  ├────────────┤  │            │  ┌──────────────────┐  │
│  │ ML 模型    │  │            │  │ 市场数据集成     │  │
│  │ (sklearn)  │  │            │  │ yfinance/akshare │  │
│  ├────────────┤  │            │  └──────────────────┘  │
│  │ LLM 引擎   │  │            │  ┌──────────────────┐  │
│  │ (OpenAI /  │  │            │  │ 知识图谱服务     │  │
│  │  Dify)     │  │            │  │ 实体-关系存储    │  │
│  └────────────┘  │            │  └──────────────────┘  │
└──────┬───────────┘            └─────────┬──────────────┘
       │                                  │
┌──────▼──────────────────────────────────▼───────────────┐
│                    数据存储层                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ PostgreSQL │  │   SQLite   │  │      Redis         │ │
│  │ (生产环境)  │  │  (开发环境) │  │  (缓存 / 队列)     │ │
│  └────────────┘  └────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 数据流向

```
新闻源 (RSS/Web)  ──►  爬虫调度器  ──►  原始数据存储
                          │
                          ▼
                     NLP 分析管道
                          │
                    ┌─────┼─────┐
                    ▼     ▼     ▼
                情感分析  实体提取  主题建模
                    │     │     │
                    └─────┼─────┘
                          ▼
                    知识图谱 + 叙事索引
                          │
                          ▼
                    API 服务  ──►  前端可视化
```

---

## 快速开始

### 环境要求

- **Python 3.11+**（推荐 3.12）
- **Node.js 18+**（推荐 20 LTS）
- **pnpm** 或 **npm**（包管理器）
- **Docker & Docker Compose**（可选，用于生产部署）

### 后端启动

```bash
# 进入后端目录
cd backend

# 复制环境配置
cp .env.example .env

# 安装依赖（推荐在虚拟环境中）
pip install -e ".[dev]"

# 启动开发服务器（默认端口 8765）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
```

启动后访问：
- API 文档：http://localhost:8765/docs
- ReDoc：http://localhost:8765/redoc

### 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器（默认端口 5173）
npm run dev
```

启动后访问：http://localhost:5173

### Docker 部署

适用于生产环境的一键部署方案：

```bash
# 在项目根目录下执行
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

Docker Compose 会启动三个服务：
- **postgres**：PostgreSQL 16 数据库（含 pgvector 扩展）
- **redis**：Redis 7 缓存和消息队列
- **backend**：FastAPI 应用（端口 8765）
- **frontend**：Nginx + Vue 3 静态文件（端口 5173）

### 使用 Make 命令

项目提供了便捷的 Make 命令：

```bash
make install    # 安装后端 + 前端依赖
make backend    # 启动后端开发服务器
make frontend   # 启动前端开发服务器
make dev        # 同时启动后端 + 前端
make test       # 运行后端测试
make lint       # 运行代码检查
make docker-up  # Docker Compose 启动
make docker-down  # Docker Compose 停止
make clean      # 清理缓存文件
```

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **后端框架** | FastAPI 0.115+ | 高性能异步 API 框架 |
| **ORM** | SQLAlchemy 2.0+ | 数据库 ORM 与迁移 |
| **数据库** | PostgreSQL 16 / SQLite | 生产 / 开发数据库 |
| **缓存** | Redis 7 | 缓存与消息队列 |
| **任务调度** | APScheduler / Celery | 定时爬虫与任务队列 |
| **NLP 规则** | jieba + 自定义词典 | 中文分词与基础情感分析 |
| **NLP 传统 ML** | scikit-learn | TF-IDF / LDA / NMF 主题建模 |
| **NLP LLM** | OpenAI API / Dify | 深度语义理解与报告生成 |
| **爬虫** | feedparser + requests + BeautifulSoup | RSS 与 Web 抓取 |
| **数据科学** | NumPy + scikit-learn | 数值计算与机器学习 |
| **前端框架** | Vue 3 (Composition API) | 用户界面 |
| **类型系统** | TypeScript 5.5+ | 前端类型安全 |
| **UI 组件** | Naive UI 2.39+ | 美观的 UI 组件库 |
| **可视化** | ECharts | 图表与知识图谱渲染 |
| **状态管理** | Pinia 2 | 前端状态管理 |
| **路由** | Vue Router 4 | 前端路由导航 |
| **HTTP 客户端** | Axios / httpx | 前后端 HTTP 通信 |
| **容器化** | Docker & Docker Compose | 生产部署 |
| **CI/CD** | GitHub Actions | 持续集成 |

---

## 项目结构

```
Finkg/
├── backend/                          # FastAPI 后端应用
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # 应用入口，FastAPI 实例
│   │   ├── config.py                 # 全局配置（Pydantic Settings）
│   │   ├── database.py               # 数据库引擎与会话管理
│   │   ├── models/                   # SQLAlchemy 数据模型
│   │   │   └── __init__.py
│   │   ├── schemas/                  # Pydantic 请求/响应 Schema
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   └── v1/                   # API v1 版本路由
│   │   │       ├── __init__.py
│   │   │       ├── router.py         # 路由聚合
│   │   │       ├── news.py           # 新闻相关 API
│   │   │       ├── analysis.py       # 分析相关 API
│   │   │       ├── narrative.py      # 叙事追踪 API
│   │   │       ├── graph.py          # 知识图谱 API
│   │   │       ├── market.py         # 市场数据 API
│   │   │       ├── report.py         # 报告生成 API
│   │   │       ├── pipeline.py       # 数据管道控制 API
│   │   │       ├── settings.py       # 系统设置 API
│   │   │       ├── status.py         # 系统状态 API
│   │   │       └── source.py         # 新闻源管理 API
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── nlp/                  # NLP 引擎
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine.py         # NLP 引擎主入口
│   │   │   │   ├── analyzer.py       # 文本分析器
│   │   │   │   └── sentiment/        # 情感分析模块
│   │   │   │       ├── __init__.py
│   │   │   │       └── rule_v2.py   # 规则引擎 v2
│   │   │   ├── crawler/              # 爬虫服务
│   │   │   │   └── __init__.py
│   │   │   ├── market/               # 市场数据服务
│   │   │   │   └── __init__.py
│   │   │   ├── narrative/            # 叙事分析服务
│   │   │   │   └── __init__.py
│   │   │   ├── graph/                # 知识图谱服务
│   │   │   │   └── __init__.py
│   │   │   ├── llm/                  # LLM 集成
│   │   │   │   ├── __init__.py
│   │   │   │   ├── openai_client.py  # OpenAI API 客户端
│   │   │   │   └── report_agent.py   # 报告生成 Agent
│   │   │   └── report/               # 报告服务
│   │   │       └── __init__.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── http.py               # HTTP 工具函数
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_crawler.py           # 爬虫测试
│   │   └── test_sentiment.py         # 情感分析测试
│   ├── .env.example                  # 环境变量模板
│   ├── Dockerfile                    # 后端 Docker 镜像
│   └── pyproject.toml                # Python 项目配置
│
├── frontend/                         # Vue 3 前端应用
│   ├── src/
│   │   ├── main.ts                   # 应用入口
│   │   ├── App.vue                   # 根组件
│   │   ├── api/
│   │   │   └── client.ts             # Axios API 客户端
│   │   ├── router/
│   │   │   └── index.ts              # Vue Router 路由配置
│   │   ├── stores/
│   │   │   └── app.ts                # Pinia 状态管理
│   │   └── views/
│   │       ├── DashboardView.vue     # 仪表盘页面
│   │       ├── NewsView.vue          # 新闻浏览页面
│   │       ├── MarketView.vue        # 市场数据页面
│   │       ├── NarrativeView.vue     # 叙事分析页面
│   │       ├── GraphView.vue         # 知识图谱页面
│   │       ├── PipelineView.vue      # 数据管道页面
│   │       ├── ReportView.vue        # 报告页面
│   │       └── SettingsView.vue      # 设置页面
│   ├── index.html                    # HTML 入口
│   ├── env.d.ts                      # 类型声明
│   ├── vite.config.ts                # Vite 构建配置
│   ├── tsconfig.json                 # TypeScript 配置
│   ├── Dockerfile                    # 前端 Docker 镜像
│   ├── nginx.conf                    # Nginx 部署配置
│   └── package.json                  # 前端依赖配置
│
├── docker-compose.yml                # Docker Compose 编排
├── Makefile                          # 便捷命令
├── sources.json                      # 默认新闻源配置
├── wechat-qr.jpg                     # 联系我们二维码
├── .gitignore
├── LICENSE
├── README.md
├── ARCHITECTURE.md
├── TUTORIAL.md
├── CONTRIBUTING.md
└── CODE_OF_CONDUCT.md
```

---

## API 端点概览

### 新闻管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/news` | 获取新闻列表（支持分页、筛选） |
| GET | `/api/v1/news/{id}` | 获取单条新闻详情 |
| POST | `/api/v1/news/fetch` | 手动触发新闻抓取 |
| GET | `/api/v1/sources` | 获取新闻源列表 |
| POST | `/api/v1/sources` | 添加新闻源 |
| PUT | `/api/v1/sources/{id}` | 更新新闻源 |
| DELETE | `/api/v1/sources/{id}` | 删除新闻源 |

### 分析服务

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/analysis/sentiment` | 情感分析 |
| POST | `/api/v1/analysis/entities` | 实体提取 |
| POST | `/api/v1/analysis/topics` | 主题建模 |
| GET | `/api/v1/narratives` | 叙事列表 |
| GET | `/api/v1/narratives/{id}` | 叙事详情与时间线 |

### 市场数据

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/market/indices` | 获取所有市场指标 |
| GET | `/api/v1/market/indices/{symbol}` | 获取单个指标详情 |

### 知识图谱

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/graph/entities` | 获取图谱实体列表 |
| GET | `/api/v1/graph/relations` | 获取实体关系 |
| GET | `/api/v1/graph/query` | 查询图谱（支持实体名、关系类型筛选） |

### 报告系统

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/reports/generate` | 生成报告 |
| GET | `/api/v1/reports` | 获取已生成报告列表 |
| GET | `/api/v1/reports/{id}` | 获取报告详情 |

### 数据管道

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/pipeline/run` | 手动执行完整数据管道 |
| GET | `/api/v1/pipeline/status` | 获取管道运行状态 |

### 系统管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/status` | 系统健康检查 |
| GET | `/api/v1/settings` | 获取系统设置 |
| PUT | `/api/v1/settings` | 更新系统设置 |

---

## 联系我们

![微信扫码联系作者](wechat-qr.jpg)

**扫码联系作者** —— 欢迎加入 Finkg 社区，交流想法、反馈问题或参与贡献！

你也可以通过以下方式联系我们：
- **提交 Issue**：在 GitHub 仓库提交功能请求或 Bug 报告
- **Pull Request**：欢迎任何形式的代码贡献
- **Discussions**：参与技术讨论和路线图规划

---

## 许可证

Finkg 基于 [MIT License](LICENSE) 开源。版权所有 (c) 2026 Finkg。

你可以自由地使用、修改和分发本软件，但需保留原始版权声明和许可证文本。本软件按"原样"提供，不提供任何明示或暗示的担保。
