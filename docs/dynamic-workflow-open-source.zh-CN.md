# dynamic workflow 正式开源：在 Dify 中用上 agent-compose

如果你已经在用 Dify 搭建 AI 应用，可能遇到过这样的场景：流程的大部分节点都很清晰，但其中某一步需要操作真实代码仓库、执行命令、使用复杂工具链，或者在多轮任务中保留工作区状态。继续往画布上增加节点，流程很快就会变得难以维护。

现在，我们将 dynamic workflow 相关能力正式开源到了 GitHub：

- 项目地址：[https://github.com/chaitin/dify-plugins](https://github.com/chaitin/dify-plugins)
- Release 下载：[https://github.com/chaitin/dify-plugins/releases/latest](https://github.com/chaitin/dify-plugins/releases/latest)
- 开源协议：Apache License 2.0

dynamic workflow 由两个可以独立安装的 Dify 插件组成：

- **agent-compose Workflow**：把 agent-compose Agent 作为一个 Tool 节点嵌入 Workflow 或 Chatflow，适合将复杂任务交给 Agent 后，再继续连接 Dify 的知识库、条件分支、模板和其他节点。
- **agent-compose Strategy**：把整个 Dify Agent 节点的执行委托给 agent-compose，适合以完整 Agent 的方式处理复杂任务，以及需要跨轮复用沙箱和工作区状态的场景。

一句话概括：Dify 继续负责低门槛的应用入口和可视化编排，agent-compose 负责在隔离沙箱中运行代码化 Agent，两个插件负责把它们连接起来。

如果想先了解我们为什么要做这件事，以及 Dify、agent-compose 和 dynamic workflow 各自解决什么问题，可以先阅读此前发布的文章：[《从拖拽式 Workflow 到代码化 Agent：用 dynamic-workflow 连接 Dify 与 agent-compose》](https://hanqing.chaitin.net/topic/3275)。本文不再展开设计背景，重点带大家完成下载、安装、配置和第一次调用。

## 开源仓库里还有什么？

本次开源仓库是长亭维护的 Dify 插件集合。目前除了两个 agent-compose 插件，还包含：

- **OctoBus**：让 Dify Agent 渐进式发现并调用 OctoBus 暴露的能力。它不会把庞大、持续变化的工具目录一次性塞进上下文，而是支持先发现能力集、查询能力说明，再按需调用具体工具。
- **Rivers IOC**：用于查询长亭百川云 Rivers 的 IP 威胁情报，支持 IPv4 和 IPv6，并以结构化 JSON 返回查询结果，方便接入 Workflow 的后续节点。

本文接下来主要介绍 agent-compose Workflow 和 agent-compose Strategy。

## 使用前准备

开始前，请确认：

1. Dify 版本为 **1.15.0 或更高版本**。
2. 已部署并启动 [agent-compose](https://github.com/chaitin/agent-compose)，且其中至少有一个可用的 Agent。
3. Dify 插件运行环境能够访问 agent-compose 的 HTTP/Connect 地址；如果服务启用了鉴权，还需要准备 Bearer Token。

> agent-compose 目前仍处于 Public Preview。建议先用于体验、内部开发和预览环境；正式用于生产前，请结合所用版本完成安全、容量、稳定性和升级验证。

## 第一步：从 Release 下载插件

打开项目的 [Releases 页面](https://github.com/chaitin/dify-plugins/releases/latest)，下载与 Agent Compose 相关的两个 `.difypkg` 文件：

```text
agent_compose_workflow-<版本号>.difypkg
agent_compose_strategy-<版本号>.difypkg
```

两个插件相互独立，可以按需安装。如果你还不确定如何选择，建议先安装 Workflow 插件：它最适合从现有工作流中挑出一个复杂步骤进行尝试。如果既想在 Workflow 中调用 Agent，又想在 Agent 节点中使用 Strategy，则两个包都需要安装。

Release 同时提供 `SHA256SUMS`，有完整性校验要求时，可以在安装前核对下载文件的 SHA-256。

## 第二步：在 Dify 中安装插件

进入 Dify 的插件管理页面，选择通过本地文件安装，上传刚刚下载的 `.difypkg`。等待安装完成后，在插件列表中应当能看到：

- `agent-compose Workflow`
- `agent-compose Strategy`

不同 Dify 小版本的按钮名称和页面位置可能略有差异，以实际界面为准。

> **【截图 1：如何安装】**
>
> 建议截图内容：Dify 插件管理页面，以及“通过本地文件安装/上传 `.difypkg`”的入口；可以在同一张图中展示两个安装包，或补一张安装完成后的插件列表。
>
> 建议图注：**在 Dify 插件管理中分别导入 agent-compose Workflow 与 agent-compose Strategy 安装包。**

## 第三步：配置 agent-compose 连接

### 配置 Workflow 插件

打开 `agent-compose Workflow` 的 Tool Provider 配置，填写：

- **agent-compose 地址**：Dify 插件运行环境可以访问的 agent-compose HTTP/Connect 基础地址。
- **agent-compose Bearer Token**：仅在 agent-compose 开启鉴权时填写。
- **超时时间秒数**：默认 `900` 秒，可根据任务耗时调整。

例如，agent-compose 在同一网络中以服务名 `agent-compose` 暴露 `17410` 端口时，地址可以是：

```text
http://agent-compose:17410
```

请特别注意：这里的地址是从 **Dify 插件运行环境** 发起访问。Dify 使用 Docker 部署时，`http://localhost:17410` 通常指向插件容器自身，并不等于宿主机或另一个容器。请根据实际部署方式使用可路由的服务名、宿主机地址或网关地址，同时限制不必要的公网暴露。

### 配置 Strategy 插件

Strategy 的连接参数位于 Dify 的 Agent 节点内部。选择 `agent-compose Strategy` 后，填写 agent-compose 地址、可选 Token 和超时时间即可。其含义与 Workflow 插件一致。

Strategy 还需要填写目标 Agent。推荐使用明确的 `project/agent` 格式，例如：

```text
adp-demo-agents/print_date
```

只有在 Agent 名称跨所有项目都唯一时，才建议省略项目前缀。

> **【截图 2：如何配置】**
>
> 建议截图内容：左侧展示 Workflow 插件的 Tool Provider 配置，框出 agent-compose 地址、Bearer Token 和超时时间；右侧展示 Strategy 节点中的对应字段，并框出 `project/agent`。
>
> 截图前请隐藏真实 Token、内网域名和其他敏感信息。
>
> 建议图注：**配置 Dify 插件可访问的 agent-compose 地址；Strategy 中还需指定 `project/agent`。**

## 示例一：在 Workflow 中调用 agent-compose Agent

假设我们希望搭建一个“代码仓库分析助手”：用户提交任务后，由 agent-compose Agent 在隔离沙箱中读取仓库、执行必要的命令，再把分析结果交还给 Dify 输出。

可以创建如下流程：

```text
开始 / 用户输入
       ↓
运行 agent-compose Agent
       ↓
答案 / 结束
```

具体操作如下：

1. 新建 Workflow 或 Chatflow，在画布中添加 Tool 节点。
2. 选择 **agent-compose Workflow → 运行 agent-compose Agent**。
3. 在 Agent 动态下拉列表中选择已经发布到 agent-compose 的 Agent。
4. 将开始节点中的用户输入绑定到 `Query`。
5. 按需填写 `Instruction`，例如“先阅读仓库说明和测试结果，再给出带文件位置的分析结论”。
6. 首次体验时，沙箱清理策略使用默认的 `stop_on_completion` 即可。
7. 将节点的 `text` 输出连接到答案或结束节点，运行一次测试。

一次成功执行会返回 Agent 的最终文本，同时提供 `run_id`、`sandbox_id`、`status`、`error` 和 `warnings` 等结构化信息，便于后续节点处理或排查问题。

> **【截图 3：使用 agent-compose Workflow 的示例】**
>
> 建议截图内容：完整 Workflow 画布，至少包含“用户输入 → 运行 agent-compose Agent → 答案”；右侧配置面板展示 Agent 动态下拉框、`Query` 变量绑定与清理策略。若画面允许，可同时保留一次成功运行的输出结果。
>
> 建议示例问题：**请分析这个仓库的测试结构，并告诉我新增一个工具插件时应补充哪些测试。**
>
> 建议图注：**将代码仓库分析任务作为 Workflow 中的一个步骤交给 agent-compose。**

## 示例二：使用 agent-compose Strategy 驱动 Agent 节点

如果核心任务本身就应该由一个完整的 agent-compose Agent 负责，可以使用 Strategy，而不是把它当作普通 Tool。

仍以“代码仓库分析助手”为例：

1. 新建 Chatflow 或包含 Agent 节点的应用。
2. 添加 Agent 节点，将 Strategy 选择为 **agent-compose Strategy**。
3. 填写 agent-compose 地址、可选 Token 和超时时间。
4. 在 `Agent` 中填写 `project/agent`。
5. 将用户输入绑定到 `Query`，按需填写 `Instruction`。
6. 选择沙箱清理策略，并将 Agent 节点的 `text` 输出连接到答案节点。
7. 运行应用并发起一次实际对话。

对于需要连续修改同一工作区、延续进程或保留文件状态的多轮任务，可以把清理策略设置为 `keep_running`。插件会按 Dify 会话、项目和 Agent 记录沙箱，后续对话可以复用同一运行环境。

> **【截图 4：使用 agent-compose Strategy 的示例】**
>
> 建议截图内容：包含 Agent 节点的 Chatflow 画布，以及节点内已选中的 `agent-compose Strategy`；框出 `project/agent`、`Query` 和 `cleanup_policy`。再展示一组连续对话或成功执行结果，用来体现完整 Agent 委托或多轮状态复用。
>
> 建议两轮示例：第一轮 **“检查仓库当前测试，并生成一份改进建议。”**；第二轮 **“基于刚才的结果，优先展开前三项。”**
>
> 建议图注：**把 Dify Agent 节点整体委托给 agent-compose，并在多轮对话中复用工作区状态。**

## 沙箱清理策略怎么选？

两个插件都提供三种策略：

| 策略 | 行为 | 推荐场景 |
| --- | --- | --- |
| `stop_on_completion` | 任务完成后停止沙箱 | 默认选择，适合大多数一次性任务 |
| `keep_running` | 任务完成后保持沙箱运行 | 需要在多轮会话中复用文件、进程或工作区状态 |
| `remove_on_completion` | 任务完成后删除沙箱 | 不需要保留环境，希望及时清理资源 |

拿不准时，先使用默认的 `stop_on_completion`。只有明确需要跨轮延续状态时再选择 `keep_running`，并同步关注沙箱资源占用和回收策略。

## Workflow 还是 Strategy？

可以用一个简单标准判断：

- **Agent 是流程中的一个复杂步骤**：选择 agent-compose Workflow。
- **这个节点本身就是一个完整 Agent**：选择 agent-compose Strategy。

如果现有 Dify Workflow 已经承载了知识检索、条件判断、内容加工和结果分发，只是其中某个节点越来越复杂，Workflow 插件通常是最自然的起点。你不需要重构整个应用，只要先把最难维护、最依赖真实运行环境的那一步交给 agent-compose。

## 写在最后

dynamic workflow 的目标并不是让大家在 Dify 和 agent-compose 之间二选一，而是让两种抽象各自处理擅长的问题：简单、明确的流程继续通过 Dify 快速搭建；需要代码表达力、真实工作区、复杂工具链和隔离沙箱的任务，则交给 agent-compose。

现在，连接两者的 agent-compose Workflow 与 agent-compose Strategy 已经开源。欢迎从 [GitHub Release](https://github.com/chaitin/dify-plugins/releases/latest) 下载 `.difypkg` 体验，也欢迎通过 Issue 和 Pull Request 反馈问题、分享使用场景并参与共建。

- GitHub：[https://github.com/chaitin/dify-plugins](https://github.com/chaitin/dify-plugins)
- Release：[https://github.com/chaitin/dify-plugins/releases/latest](https://github.com/chaitin/dify-plugins/releases/latest)
- 原理介绍：[https://hanqing.chaitin.net/topic/3275](https://hanqing.chaitin.net/topic/3275)
