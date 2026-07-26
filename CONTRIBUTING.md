# 贡献指南 | Contributing Guide

欢迎你为 Finkg 项目做出贡献！这份指南将帮助你了解如何参与开发。

Welcome to Finkg! We appreciate your interest in contributing. This guide will help you get started.

---

## 中文版本

### 如何贡献

Finkg 欢迎任何形式的贡献，包括但不限于：

- **提交 Bug 报告**：通过 GitHub Issues 提交详细的问题描述
- **功能建议**：提出新功能的想法和改进建议
- **代码贡献**：修复 Bug、实现新功能、优化性能
- **文档改进**：修正错别字、补充文档、改善教程
- **测试覆盖**：编写单元测试和集成测试
- **代码审查**：审查他人的 Pull Request

### 开发环境搭建

参见 [TUTORIAL.md](TUTORIAL.md) 中的详细步骤。

快速回顾：

```bash
# Fork 并克隆仓库
git clone https://github.com/your-username/finkg.git
cd finkg

# 安装后端依赖
cd backend
cp .env.example .env
pip install -e ".[dev]"

# 安装前端依赖
cd ../frontend
npm install

# 运行测试确保一切正常
cd ../backend
python -m pytest -v
```

### 编码规范

#### Python 后端

1. **Python 版本**：3.11+
2. **代码风格**：遵循 PEP 8，使用 Ruff 进行格式化和检查
3. **类型注解**：所有函数参数和返回值必须包含类型注解
4. **文档字符串**：使用 Google 风格的 Docstring
5. **命名规范**：
   - 模块名：小写 + 下划线（`news_analyzer.py`）
   - 类名：驼峰式（`NewsAnalyzer`）
   - 函数/变量：小写 + 下划线（`analyze_sentiment()`）
   - 常量：大写 + 下划线（`MAX_RETRY_COUNT`）
6. **测试**：新功能必须包含单元测试，测试文件以 `test_` 开头
7. **依赖**：新增依赖需添加到 `pyproject.toml` 中

**运行代码检查：**

```bash
cd backend
ruff check .
ruff format .
```

#### TypeScript / Vue 前端

1. **TypeScript**：严格模式，所有变量必须有类型声明
2. **Vue 组件**：使用 Composition API + `<script setup>` 语法
3. **命名规范**：
   - 组件文件：PascalCase（`DashboardView.vue`）
   - 函数/变量：camelCase（`getNewsList()`）
   - 类型接口：PascalCase 以 `I` 前缀（`INewsItem`）
4. **状态管理**：优先使用 Pinia，避免组件间直接传递过多 props
5. **样式**：使用 Naive UI 内置主题，避免全局 CSS 污染

**运行代码检查：**

```bash
cd frontend
npm run lint
npm run type-check
```

### Pull Request 流程

1. **Fork 仓库**：点击 GitHub 页面右上角的 Fork 按钮
2. **创建分支**：从 `main` 分支创建功能分支
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **提交更改**：使用清晰、描述性的提交信息
   ```bash
   git commit -m "feat: add support for xxx"
   ```
4. **推送到远程**：
   ```bash
   git push origin feature/your-feature-name
   ```
5. **创建 Pull Request**：在 GitHub 上创建 PR，描述清楚变更内容

### PR Checklist

提交 PR 前，请确认以下事项：

- [ ] 代码通过 Ruff 检查（`ruff check .`）
- [ ] 代码通过 Ruff 格式化（`ruff format .`）
- [ ] 所有测试通过（`pytest -v`）
- [ ] 新功能包含单元测试
- [ ] 添加了类型注解和 Docstring
- [ ] 前端通过类型检查（`npm run type-check`）
- [ ] 更新了相关文档（如果需要）
- [ ] PR 标题遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范

### 提交信息规范

我们推荐使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <description>

[optional body]
```

类型（type）包括：
- `feat`：新功能
- `fix`：Bug 修复
- `docs`：文档变更
- `style`：代码格式调整（不影响功能）
- `refactor`：代码重构
- `test`：测试相关
- `chore`：构建/工具链变更
- `perf`：性能优化

示例：
- `feat(api): add sentiment analysis endpoint`
- `fix(crawler): handle RSS encoding error`
- `docs(readme): update quick start guide`

### 行为准则

所有贡献者必须遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 中的行为准则。

---

## English Version

### How to Contribute

Finkg welcomes contributions of all forms, including but not limited to:

- **Bug Reports**: Submit detailed issue descriptions via GitHub Issues
- **Feature Suggestions**: Propose new feature ideas and improvements
- **Code Contributions**: Fix bugs, implement features, optimize performance
- **Documentation**: Fix typos, expand docs, improve tutorials
- **Test Coverage**: Write unit and integration tests
- **Code Review**: Review Pull Requests from other contributors

### Development Setup

See [TUTORIAL.md](TUTORIAL.md) for detailed setup instructions.

Quick recap:

```bash
# Fork and clone the repository
git clone https://github.com/your-username/finkg.git
cd finkg

# Install backend dependencies
cd backend
cp .env.example .env
pip install -e ".[dev]"

# Install frontend dependencies
cd ../frontend
npm install

# Run tests to verify everything works
cd ../backend
python -m pytest -v
```

### Coding Standards

#### Python Backend

1. **Python Version**: 3.11+
2. **Code Style**: PEP 8 compliant, using Ruff for linting and formatting
3. **Type Hints**: All function parameters and return values must have type annotations
4. **Docstrings**: Google-style docstrings
5. **Naming Conventions**:
   - Modules: lowercase_with_underscore (`news_analyzer.py`)
   - Classes: PascalCase (`NewsAnalyzer`)
   - Functions/Variables: lowercase_with_underscore (`analyze_sentiment()`)
   - Constants: UPPERCASE_WITH_UNDERSCORE (`MAX_RETRY_COUNT`)
6. **Testing**: New features must include unit tests, test files prefixed with `test_`
7. **Dependencies**: Add new dependencies to `pyproject.toml`

**Run code checks:**

```bash
cd backend
ruff check .
ruff format .
```

#### TypeScript / Vue Frontend

1. **TypeScript**: Strict mode, all variables must have type declarations
2. **Vue Components**: Use Composition API with `<script setup>` syntax
3. **Naming Conventions**:
   - Component files: PascalCase (`DashboardView.vue`)
   - Functions/Variables: camelCase (`getNewsList()`)
   - Type interfaces: PascalCase with `I` prefix (`INewsItem`)
4. **State Management**: Prefer Pinia over excessive prop drilling
5. **Styling**: Use Naive UI built-in theme, avoid global CSS pollution

**Run code checks:**

```bash
cd frontend
npm run lint
npm run type-check
```

### Pull Request Process

1. **Fork the Repository**: Click the Fork button in the top-right corner
2. **Create a Branch**: Create a feature branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit Changes**: Use clear, descriptive commit messages
   ```bash
   git commit -m "feat: add support for xxx"
   ```
4. **Push to Remote**:
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Create a Pull Request**: Open a PR on GitHub with a clear description

### PR Checklist

Before submitting your PR, please confirm:

- [ ] Code passes Ruff checks (`ruff check .`)
- [ ] Code is Ruff formatted (`ruff format .`)
- [ ] All tests pass (`pytest -v`)
- [ ] New features include unit tests
- [ ] Type hints and docstrings are added
- [ ] Frontend passes type checking (`npm run type-check`)
- [ ] Related documentation is updated (if needed)
- [ ] PR title follows [Conventional Commits](https://www.conventionalcommits.org/) spec

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (no functional impact)
- `refactor`: Code refactoring
- `test`: Test-related changes
- `chore`: Build/toolchain changes
- `perf`: Performance improvements

Examples:
- `feat(api): add sentiment analysis endpoint`
- `fix(crawler): handle RSS encoding error`
- `docs(readme): update quick start guide`

### Code of Conduct

All contributors must adhere to the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
