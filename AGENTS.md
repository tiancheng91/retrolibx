# AGENTS.md

This file provides guidance to coding agents working in this repository.

## 项目概述

RetroLibX（Retro Library Exchange）是一个 Python 3.12+ 命令行工具，用于在不同复古游戏前端和游戏库格式之间迁移：

- ROM 与多文件游戏引用
- 游戏元数据
- 封面、截图、标题图、视频和手册
- Collection / Playlist
- Core、Emulator 与启动配置
- 收藏状态和游玩统计

V1 支持 RetroArch、通用 EmulationStation、ROCKNIX、ES-DE 和 Pegasus。

所有转换必须遵循：

```text
Source → RetroLibX IR → Target
```

禁止新增格式之间的点对点转换器，例如 `RetroArchToPegasusConverter`。

## 常用命令

```bash
# 安装锁定依赖
uv sync --locked

# 查看 CLI
uv run retrolibx --help

# 检测和扫描游戏仓库
uv run retrolibx detect /path/to/library
uv run retrolibx scan /path/to/library
uv run retrolibx scan /path/to/library --json

# 非标准 RetroArch playlist：指定游戏名字段
uv run retrolibx scan /path/to/library --game-name-field core_name

# 转换前预览（不得写文件）
uv run retrolibx convert /path/to/source \
  --to rocknix \
  --output /path/to/target \
  --dry-run

# 执行转换
uv run retrolibx convert /path/to/source \
  --to rocknix \
  --output /path/to/target

# 完整验证
uv run pytest --cov=retrolibx --cov-fail-under=80
uv run ruff check .
uv run ruff format --check .
uv run mypy src

# 运行单个测试
uv run pytest tests/test_adapters.py::test_retroarch_import_and_render -v

# 构建 PyPI 包
uv build
```

若当前网络访问官方 PyPI 较慢，可仅对当前命令使用中科大镜像，不要擅自修改用户全局配置：

```bash
UV_DEFAULT_INDEX=https://mirrors.ustc.edu.cn/pypi/simple uv sync --locked
```

## 核心架构约束

项目必须长期维持三个边界。

### 1. 统一 IR

`src/retrolibx/core/models.py` 定义 RLX IR：

- `Library` — 来源格式、系统、Collection、全局元数据和诊断
- `System` — canonical system ID、展示名和游戏列表
- `Game` — 游戏名、ROM、媒体、基础元数据、游玩状态和启动配置
- `Rom` — 文件路径、大小、hash、碟号和来源元数据
- `Media` — 语义化媒体字段，不保存平台特有文件夹名称
- `Collection` — 通过稳定 ID 引用游戏
- `LaunchConfig` — emulator、core、command、工作目录和参数

Adapter 之间不能互相依赖。所有来源先导入 RLX IR，再由目标 Adapter 渲染。

Pydantic 模型中的可变字段必须使用 `Field(default_factory=...)`，禁止共享列表或字典默认值。

### 2. Adapter 与 Profile 分离

`src/retrolibx/adapters/base.py` 定义 `LibraryAdapter`：

- `detect(path)` — 返回格式、0~1 置信度和识别证据
- `import_library(path, options)` — 来源格式转换为 RLX IR
- `render_library(library, target, options)` — RLX IR 转为声明式 `ExportIntent`
- `capabilities` — 声明目标可表达的数据能力

内置 Adapter 注册在 `src/retrolibx/adapters/registry.py`，格式名称和别名必须通过注册表解析，不要添加长 `if/elif` 分支。

格式和平台约定需要区分：

- EmulationStation Adapter 负责 `gamelist.xml` 语法
- ROCKNIX 复用 EmulationStation XML codec，但维护独立平台目录约定
- ES-DE 复用 XML 基础能力，但保持独立 Adapter、检测和媒体规则

添加新平台时优先组合共享 codec，不要复制完整 parser，也不要让通用格式承担发行版特有规则。

### 3. Plan 与 Execute 分离

写文件流程必须保持：

```text
Library
  ↓
Target Adapter → ExportIntent
  ↓
ConversionPlanner → ConversionPlan
  ↓
PlanExecutor → Target
```

关键文件：

- `core/operations.py` — ExportIntent、操作模型和执行报告
- `core/planner.py` — 目标路径、冲突策略、Manifest 和操作计划
- `core/executor.py` — 唯一允许修改目标文件系统的组件

Adapter 不得调用 `shutil.copy`、`Path.write_text` 或直接创建目标目录。`--dry-run` 必须只创建计划，不能产生任何目标文件。

## 仓库与文件发现

`src/retrolibx/utils/discovery.py` 提供统一递归发现和文件索引。

元数据从用户给定的来源根目录递归查找：

- `*.lpl`
- `gamelist.xml`
- `metadata.pegasus.txt`

忽略 `.git`、`.retrolibx`、`.venv` 和 `__pycache__`。不要重新引入只扫描直属目录或固定一层目录的限制。

ROM 和媒体路径按以下顺序解析：

1. 已存在的绝对路径
2. 相对元数据目录或已识别前端根目录
3. 相对用户传入的仓库根目录
4. 最长路径尾部唯一匹配，用于处理 `/storage/roms` 等失效设备根路径
5. 唯一文件名匹配，并结合 ROM、封面、截图、视频等语义目录提示

多个候选仍有歧义时不得猜测，应保留未解析引用，让 validation 输出诊断。

内部成功解析的路径统一保存为绝对 `Path`，但来源元数据可以使用绝对路径、相对路径或已失效的设备路径。

## RetroArch

实现位于 `src/retrolibx/adapters/retroarch/`：

- `playlist.py` — `.lpl` JSON codec
- `media.py` — `Named_Boxarts`、`Named_Snaps`、`Named_Titles` 解析
- `adapter.py` — detection、IR 映射和导出意图

标准字段映射：

```text
label      → Game.name
path       → Rom.path
core_name  → LaunchConfig.core
core_path  → LaunchConfig.metadata["core_path"]
crc32      → Rom.crc32
db_name    → source_metadata
```

部分第三方 playlist 会把游戏名错误存入 `core_name`。`ImportOptions.game_name_field` 和 CLI `--game-name-field` 允许用户指定来源字段：

```bash
uv run retrolibx scan SOURCE --game-name-field core_name
```

注意：自定义游戏名字段只改变 `Game.name`。缩略图仍使用原始 `label` 匹配，否则 `GBA 225.png` 等资源会失配。原始资源标签和所选字段保存在 `source_metadata["retroarch"]`。

## EmulationStation、ROCKNIX 与 ES-DE

`src/retrolibx/adapters/emulationstation/gamelist.py` 是共享 XML codec。

XML 解析必须：

- 禁止网络访问
- 禁止 DTD 加载和外部实体解析
- 保持确定性的元素顺序和 UTF-8 输出
- 未知来源字段保留到 namespaced `source_metadata`，但未经 allowlist 不写回标准 XML

通用 EmulationStation 不应隐含 ROCKNIX 或 ES-DE 的固定目录规则。

## Pegasus

`src/retrolibx/adapters/pegasus/metadata.py` 负责 stanza 格式：

- 支持重复字段
- 支持缩进续行
- Collection 默认值和 game 字段分开处理
- 输出字段及游戏排序必须确定

`adapter.py` 负责系统映射、ROM、媒体、基础元数据和 launch command 转换。

## System Registry

`src/retrolibx/registry/systems.yaml` 是 canonical system ID 的唯一配置来源。Adapter 不应硬编码平台别名和目录映射。

每条系统配置包含：

- canonical ID 和显示名
- aliases
- ROM extensions
- RetroArch playlist 名称
- ROCKNIX / ES-DE 目录
- Pegasus shortname

新增系统时同时添加 registry 测试，特别关注别名冲突。含糊别名必须报错，不能静默选择第一个结果。

## 安全原则

- 默认不删除、覆盖或修改来源库
- source 与 target 相同默认拒绝，除非显式、安全地使用 `--in-place`
- 所有目标路径必须限制在 target root 内，并在计划和执行阶段重复验证
- 冲突必须在执行前按 `skip`、`overwrite`、`rename`、`error` 或 `newer` 解析
- 元数据和 Manifest 使用临时同级文件后原子替换
- Manifest 最后写入，用于表示受管导出已经完成
- 导入的 launch command 只作为数据保存，绝不执行
- 单个游戏的解析错误尽量转为带上下文的 `Diagnostic`，不要无条件中止整个库

## CLI 与错误处理

入口为 `retrolibx.cli:run`，命令包括：

- `detect`
- `scan`
- `convert`
- `inspect`
- `validate`

人类输出使用 Rich，`--json` 输出可机器读取的结构。用户来源文本不得作为 Rich markup 直接解释。

预期业务错误继承 `RetroLibXError`，CLI 映射稳定退出码：

- `1` — validation error 或部分执行失败
- `2` — CLI 用法错误
- `3` — detection / parse failure
- `4` — 不安全计划或未解决冲突

除非启用 debug，不应向普通用户显示 traceback。

## 测试

测试目录：

- `tests/test_models_registry.py` — IR、normalization 和 system registry
- `tests/test_planner_executor.py` — dry-run、安全边界、冲突和文件模式
- `tests/test_adapters.py` — 五种 Adapter、递归发现、路径回退和自定义字段
- `tests/test_service_cli.py` — application service、CLI 和端到端转换

每次变更至少运行与修改范围相关的测试；提交或发布前必须运行完整验证。覆盖率门槛是 80%。

涉及 Adapter 时，应至少覆盖：

- detection
- Source → RLX IR
- RLX IR → ExportIntent
- 非标准或缺失字段
- 失效绝对路径和相对路径
- 同格式语义 round-trip（适用时）
- 确定性输出或 golden file

涉及 Planner/Executor 时必须证明 dry-run 零写入、来源安全和路径不可逃逸。

## 发布流程

`.github/workflows/ci.yml` 在 main push 和 PR 上运行：

- pytest + coverage ≥ 80%
- Ruff lint 与格式检查
- strict mypy
- `uv build` 构建验证（该产物不作为正式发布包）

`.github/workflows/publish.yml` 仅在 `v*` tag 上运行：

- 校验 tag 与 `pyproject.toml` 版本一致
- 对 tag 指向的源码重新运行测试、Ruff、格式和 strict mypy
- 对 tag 指向的源码重新构建正式 wheel 和 sdist
- 通过 Artifact 将正式构建产物传递给独立 publish job
- 通过 PyPI Trusted Publishing 发布

每次 release：

1. 更新 `pyproject.toml` 中的 `project.version`
2. 将 `CHANGELOG.md` 的用户可见变更从 `Unreleased` 移入带 ISO 日期的版本章节
3. 运行完整验证和 `uv build`
4. 提交版本号和 changelog：`git commit -m "chore: release x.y.z"`
5. 创建并推送匹配标签：`git tag vx.y.z && git push origin vx.y.z`

工作流会校验 tag 去掉 `v` 后必须与包版本完全一致。Tag 必须指向包含版本号更新的 commit。

PyPI Trusted Publisher 配置应使用：

```text
Owner: tiancheng91
Repository: RetroLibX
Workflow: publish.yml
Environment: pypi
```

## 设计与任务文档

V1 的需求、技术方案和完成记录位于：

- `CHANGELOG.md` — 遵循 Keep a Changelog，记录用户可见版本变化
- `specs/v1/requirements.md`
- `specs/v1/design.md`
- `specs/v1/tasks.md`

架构或范围发生实质变化时同步更新这些文档，不要只修改代码。
