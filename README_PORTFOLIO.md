# Chatty Engineering Agent

> 基于开源 Chatty 二次开发的工程执行型 AI
> Agent：从自然语言需求出发，自主调查已有代码库，提出最小修改，在人工审批后执行写操作，并完成验证与结果汇报。

**核心目标不是做一个代码问答机器人，而是把大模型接入一个受控、可恢复、可验证的工程执行
Runtime。**

> 🎬 **Demo Video：** 已完成，发布链接待补充
> 🧪 **Demo Stability Check：** 正式录制前独立运行 3 次，3/3 完成完整工程流程

```{=html}
<!-- 正式录制后可在这里加入 docs/images/engineering-agent-demo.gif -->
```
## Highlights

-   **Engineering Agent** ---
    将用户的大白话需求转化为工程任务，自主搜索、阅读代码并基于现有架构决定实现方案。
-   **Controlled Write Workflow** --- 项目写操作采用
    `Preview → Approve → Apply`，模型不能未经确认直接修改代码。
-   **Continuation Recovery** --- 写操作成功后先持久化 Tool
    Result；即使前端刷新中断当前请求，也能从已完成的副作用之后继续，避免重复写入。
-   **Extended Provider Architecture** --- 在 Chatty 原有 Provider
    架构基础上扩展 OpenAI-Compatible 抽象，并接入 DeepSeek、Kimi、GLM
    等模型，同时完善 Ollama 本地模型使用路径。
-   **Technical Agent Eval** --- 建立 11-case Tech v1 Eval，通过真实
    Chatty Runtime 评估需求理解、调查、工程决策、验证与收敛等行为。

------------------------------------------------------------------------

## What I Changed

Chatty 原项目已经提供 React / FastAPI
应用、Agent、Conversation、Context、Tool / Integration 以及多 Provider
等基础能力。本项目不是从零实现新的 Agent
Framework，而是在理解原有架构的基础上，重点扩展
**模型接入、工程执行、安全写入、运行可靠性与 Agent Eval**。

### 1. Provider Architecture Extension

在原有 Provider 体系上进一步抽象 OpenAI-Compatible
模型通道，使不同兼容模型能够复用统一的流式响应、Tool Calling 和 Tool
Result 处理逻辑。

-   抽象 OpenAI-Compatible Provider 公共逻辑
-   接入 DeepSeek、Kimi、GLM 等 OpenAI-Compatible 云模型
-   完善原有 Ollama 本地模型接入流程，可发现本机模型并在设置页选择，并使用本地 `qwen3:8b` 验证调用链路
-   保持上层 Agent Runtime 与具体 Provider 解耦

### 2. Engineering Agent & Project Tooling

构建面向已有代码库的 Tech
Agent，使其能够从自然语言需求出发完成工程调查和受控修改。

``` text
Natural-language Request
        ↓
Codebase Investigation
        ↓
Evidence-based Decision
        ↓
Minimal Change
        ↓
Validation
        ↓
Final Report
```

项目工程工具覆盖：

-   **Search** --- 搜索项目代码和已有实现模式
-   **Read** --- 阅读相关文件和上下文
-   **Preview** --- 写入前生成修改预览
-   **Write** --- 经批准后执行 Edit / Create
-   **Run** --- 执行 Build / Test / Script 等验证命令
-   **Git** --- 检查 Diff / Status，确认最终修改范围

Tech Agent
的设计原则是：**能够通过代码调查解决的工程问题优先自主调查；只有产品意图存在关键歧义时才向用户确认。**

### 3. Human-in-the-loop Write & Continuation Recovery

将有副作用的项目写操作放入受控执行流程：

``` text
Preview
   ↓
User Approve
   ↓
Apply
   ↓
Persist Tool Result
   ↓
Continue Agent Turn
```

写操作不会由模型未经确认直接落盘。Runtime 先生成
Preview，由用户批准后才执行实际修改。

同时针对前端代码修改可能触发页面刷新、导致当前 Agent
请求中断的问题，增加 Continuation Recovery：成功的 Tool Result
会先持久化，恢复时从已经完成的副作用之后继续，而不是重放整个 Turn。

### 4. Technical Agent Eval

建立 Tech v1 Evaluation，通过真实 Chatty Agent Runtime
执行工程任务，而不是只对最终回答文本评分。

评估覆盖需求理解、澄清判断、自主调查、证据判断、修改决策、验证与收敛，并保留失败、部分完成以及
max-iteration 等真实运行结果。

------------------------------------------------------------------------

## Architecture

![Chatty Engineering Agent
Architecture](docs/images/chatty-engineering-agent-architecture.png)

整体设计将 **模型决策能力** 与 **工程执行 Runtime** 分离：

-   `Engineering Agent` 负责理解需求、调查代码并基于证据做工程决策。
-   `Agent Runtime` 负责 Tool Loop、写操作审批、Tool Result
    持久化、Continuation Recovery 与 Validation。
-   `Provider Layer` 将 OpenAI-Compatible 云模型与 Ollama
    本地模型接入统一 Runtime。
-   `Technical Agent Eval` 运行在真实 Agent Runtime
    上，评估完整执行行为，而不是只比较最终回答。

------------------------------------------------------------------------

## Engineering Agent Demo

下面使用前端国际化改造过程中发现的一个真实问题，展示完整
Engineering Agent 工作流。

> **用户需求：**\
> 中文界面下，左侧 `+ New chat` 按钮仍然显示英文，希望它正确显示为
> `+ 新建对话`。

用户只描述界面现象，没有提供文件名、组件名、i18n key 或具体实现方案。

``` text
Natural-language Request
        ↓
Search Project Code
        ↓
Read Relevant Files
        ↓
Identify Existing i18n Pattern
        ↓
Determine Minimal Change
        ↓
Preview
        ↓
User Approve
        ↓
Apply
        ↓
Frontend Build
        ↓
Git Diff
        ↓
Final Report
```

### Investigation

Agent 调查后发现：

-   `ConversationSidebar.tsx` 已经使用 `useTranslation()`
-   `conversationSidebar.newChat` 已经同时存在于中英文 locale
-   UI 中的 `+ New chat` 仍然是硬编码文本

因此不需要新增翻译资源，也不需要修改 i18n 架构。

### Minimal Change

最终修改只有一处：

``` diff
- + New chat
+ + {t('conversationSidebar.newChat')}
```

实际写入前，Runtime 首先生成 Preview，并等待用户明确批准：

``` text
Preview → Approve → Apply
```

### Validation

修改完成后执行与变更范围匹配的验证：

``` text
Frontend Build  ✓
Git Diff        ✓
```

最终 Git Diff 仅包含预期的单点修改。

``` text
中文：+ 新建对话
英文：+ New chat
```

**Demo Stability Check：3/3**

正式录制前，在相同模型、Agent 配置和任务下进行了 3 次独立稳定性测试，
3 次均完成完整工程流程。

------------------------------------------------------------------------

## Runtime Reliability

Agent 工程执行不仅需要处理"Tool 是否执行成功"，还需要处理：

> **Tool 已经成功产生副作用，但整个 Agent Turn
> 因页面刷新等原因没有正常结束，怎么办？**

### The Problem

``` text
Agent
  ↓
Preview
  ↓
User Approve
  ↓
Write succeeds ✓
  ↓
Vite reload / request interrupted
```

如果恢复方式只是重新执行整个 Agent Turn：

``` text
Retry whole turn
      ↓
Execute write again ✗
```

就可能重复执行已经成功的副作用。

### Continuation Recovery

Runtime 将 **Tool Success** 和 **Agent Turn Success** 分开处理：

``` text
Write succeeds
      ↓
Persist Tool Result
      ↓
Mark continuation_pending
      ↓
Request interrupted / page reload
      ↓
Restore Conversation
      ↓
Detect continuation_pending
      ↓
Resume with continuation_resume=true
      ↓
Continue after persisted Tool Result
```

恢复时不会重新发送原始用户请求并从整个 Turn 起点重跑，而是从已经持久化的
Tool Result 之后继续。

### Reproduction

使用独立 controlled fixture 验证该流程：

> **用户需求：**\
> 中文界面下，把项目页面的标题改成"项目 ·
> Demo"，英文界面保持原样，其他内容和行为不要改。

Agent 自主调查后定位到已有 i18n 资源，并只修改中文 locale：

``` diff
- "title": "项目",
+ "title": "项目 · Demo",
```

实际执行：

``` text
Preview
   ↓
Approve
   ↓
Write ✓
   ↓
Vite automatically reloads the page
   ↓
Original conversation restored
   ↓
Continuation automatically resumed
   ↓
No duplicate write
   ↓
Agent completes
```

最终：

``` text
中文：项目 · Demo
英文：Project
```

这个场景用于验证：**即使写操作之后的 Agent 请求被前端刷新中断，Runtime
仍能保留已经完成的副作用并安全继续执行。**

------------------------------------------------------------------------

## Technical Agent Eval

为了避免只通过 Demo 或最终回答主观判断 Agent 效果，我建立了 **Tech v1
Evaluation**。

Eval 直接通过真实 Chatty Agent Runtime
执行任务，关注的不只是最终回答是否正确，也记录 Agent
在工程执行过程中的调查、Tool Calling、写操作、Validation 和 Convergence
行为。

### Evaluation Scope

当前 Tech v1 包含：

-   **11 个正式 Cases**
-   **7 个核心评估维度**
-   **3 个经过真实写入流程验证的 Cases**
-   Read-only investigation 与 write workflow
-   Tool execution / completion / iteration 等运行信息

| Dimension | 关注点 |
| --- | --- |
| Requirement Understanding | 是否正确理解用户真正想解决的问题 |
| Clarification Judgment | 是否只在产品意图存在关键歧义时询问用户 |
| Autonomous Investigation | 是否能够自主调查代码库，而不是把工程问题推回用户 |
| Evidence Judgment | 是否知道已有证据何时足以支持结论 |
| Change Decision | 是否选择符合现有架构的最小修改 |
| Validation | 是否执行与修改范围匹配的验证，并正确解释结果 |
| Convergence | 是否能够在获得充分证据后停止调查并完成任务 |

评分尺度：`2 = Pass` · `1 = Partial` · `0 = Fail` ·
`N/A = Not Applicable`

### Representative Results

| Case | Capability | Result |
| --- | --- | --- |
| `TECH-REQ-01` | Requirement understanding | 83.3% · Completed |
| `TECH-CLARIFY-01` | Product ambiguity judgment | 91.7% · Completed |
| `TECH-ARCH-01` | Architecture judgment | 90.0% · Completed |
| `TECH-CONV-01` | Execution convergence | 50.0% · Max iteration |
| `TECH-SCOPE-01` | Scope control / write | 90.0% · Completed |
| `TECH-WRITE-01` | Full write workflow | 83.3% · Completed |
| `TECH-VALID-01` | Validation judgment | 50.0% · Completed |

> `TECH-REF-01` 的历史 numeric score 未被可靠保存，因此不人为补算分数。

### What the Eval Found

表现较好的能力：

-   Requirement understanding
-   Autonomous codebase investigation
-   Architecture judgment
-   Minimal-change implementation
-   Write approval & continuation execution
-   Basic validation selection

当前已知弱点：

-   Evidence boundary judgment
-   Execution convergence
-   长 Tool Loop 下的 write-state tracking
-   产品意图真正存在歧义时的 clarification discipline
-   Validation command 因无关代码失败时的结果表述精度
-   多步 Tool Calling 过程中的语言一致性

失败和部分完成结果会保留在 benchmark 中，而不是从展示结果中删除。

### Model Behavior Comparison

在相同 Runtime 和 Case 定义下，对 DeepSeek v4 Flash 与 GLM-5.3
做了三个代表性 Case 的对照：

| Case | DeepSeek v4 Flash | GLM-5.3 |
| --- | --- | --- |
| `TECH-CONV-01` | 50.0% · Max iteration | **100.0% · Completed** |
| `TECH-VALID-01` | 50.0% · Completed | **64.3% · Completed** |
| `TECH-WRITE-01` | **83.3% · Completed** | 41.7% · Max iteration |

这个对比不是为了给模型做综合排名，而是观察：

> **在固定 Agent Runtime 后，不同模型在工程判断、Tool Loop
> 收敛和写操作任务上的行为差异。**

------------------------------------------------------------------------

## Additional Work

除 Engineering Agent Runtime 外，还基于 Chatty 原有架构进行了以下扩展。

### Local Model Support

完善 Ollama 本地模型接入，使 Chatty 可以不依赖云端 API Key
使用本机模型。

-   自动检测本地 Ollama 服务及可用模型
-   在 Settings 中直接连接和选择本地模型
-   本地模型与云端 Provider 共用上层 Agent Runtime
-   使用本地 `qwen3:8b` 验证模型调用链路

``` text
Chatty Agent
     ↓
Provider Interface
     ↓
Ollama Provider
     ↓
localhost:11434
     ↓
Local Model
```

### Feishu / WeCom Integration Work

参考 Chatty 原有 Integration 架构，扩展国内协作平台接入：

-   Feishu：接入 SDK 与长连接消息链路
-   WeCom：按平台能力适配消息接入方式
-   将外部平台消息接入已有 Agent processing flow
-   尽量保持 Integration 与 Agent Runtime 的职责边界

> 这部分属于扩展与验证工作，不声明为 production-ready integration。

### Frontend Internationalization

为前端引入 `i18next / react-i18next`，逐步将硬编码 UI 文本迁移到统一
locale 资源。

主要覆盖：

-   English
-   简体中文
-   Settings / Agent / Integration 等主要界面国际化
-   运行时语言切换

Engineering Agent Demo 中展示的 `+ New chat → + 新建对话`
也是这套实际 i18n 改造中的真实修复。

------------------------------------------------------------------------

## Upstream & Contribution Boundary

本项目基于开源项目 **Chatty** 进行架构分析和二次开发。

原项目已经提供 React / FastAPI 应用基础、Agent /
Conversation、Context、Tool / Integration、多 Provider、CRM、Reminders
等能力。本仓库重点展示的是在理解现有系统后完成的工程扩展，而不是将原项目能力声明为从零实现。

### 本项目重点改造

-   OpenAI-Compatible Provider abstraction 与兼容模型扩展
-   DeepSeek / Kimi / GLM 等模型接入工作
-   Ollama local-model workflow enhancement
-   Engineering-oriented Tech Agent
-   Project investigation / write / validation workflow
-   Human-in-the-loop write approval
-   Continuation Recovery
-   Technical Agent Eval
-   Frontend internationalization
-   Feishu / WeCom integration work

### Existing Chatty Foundation

主要来自 upstream Chatty、并作为本次改造基础的能力包括：

-   React / FastAPI application shell
-   Base Agent / conversation system
-   Existing Context architecture
-   Existing Tool / Integration infrastructure
-   Existing multi-provider foundation
-   Existing application UI and general product structure

Upstream: https://github.com/WWilson1017/chatty

------------------------------------------------------------------------

## Quick Start

``` bash
git clone <your-portfolio-repository-url>
cd chatty
python run.py
```

`run.py` 会检查 prerequisites、创建 virtual
environment、安装依赖并启动服务。启动完成后访问：

`http://localhost:8000`

### Requirements

-   Python 3.10+
-   Node.js 18+

### Configuration

复制 `.env.example` 为 `.env`，并按需要配置登录凭据和模型 Provider。

至少配置一个可用的 AI Provider，或使用本地 Ollama。

> 请勿将真实 API Key、OAuth credential 或本地敏感配置提交到仓库。

### Using Ollama

1.  安装 Ollama
2.  拉取支持 Tool Calling 的模型
3.  启动 Chatty
4.  在 Settings 中连接 Ollama 并选择本地模型

本项目开发过程中使用 `qwen3:8b` 验证过本地模型调用链路。

------------------------------------------------------------------------

## Upstream Documentation

Chatty upstream 还提供 CRM、Heartbeat、Reminders、Google
integrations、Telegram、Paperclip、Railway deployment
等能力。这些不是本求职项目的主要改造范围。

完整功能与部署说明请参考：

-   Upstream repository: https://github.com/WWilson1017/chatty
-   [`docs/`](docs/)
-   [`DEPLOY.md`](DEPLOY.md)

------------------------------------------------------------------------

## Contributing

参见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## Security

安全问题参见 [`SECURITY.md`](SECURITY.md)。

## License

本项目沿用 upstream Chatty 的 [MIT License](LICENSE)。
