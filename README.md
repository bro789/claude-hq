# 指挥中心 claude-hq

多个 Claude Code 对话同时干活时，常常会抢同一块显卡、同一个端口。claude-hq 让其中一个对话当**指挥中心**，统一管理 GPU、端口、模型服务和共享代码。其他对话用这些公共资源之前先向它申请，拿到批准再用，用完释放。整套机制只靠几份规则文件、对话之间的消息和写在磁盘上的账本，不用另外部署服务。

**English summary.** claude-hq is a set of rule files that turns one Claude Code session into a "headquarters" (指挥中心) for the other sessions on the same machine. A worker session sends a request before it uses a shared resource: GPU memory, a port, a model server, or shared code or environments. The headquarters approves the request, queues it, or schedules it. It then checks the started process by PID, command line and start time, and records everything on disk. claude-hq runs on the Claude desktop app's cross-session messaging. The rules and the message protocol are written in Chinese.

## 为什么需要
同时开好几个对话、各推进一个项目时，它们会：
- 同时往一张显卡上加载模型，把显存挤爆；
- 抢同一个端口；
- 一个在改共享的虚拟环境，另一个正好在用；
- 各起一份相同的模型服务，白占显存。

## 怎么工作
- **一个指挥中心，多个工作对话。** 指挥中心的会话名是 `指挥中心-<编号>`，同一时间只有一个在岗。新指挥中心上岗时，会自动关闭旧的，并邀请旧成员加入。
- **先申请，后使用。** 显存按 GB 分配，端口独占，共享文件加写锁。批准后 10 分钟内必须启动并回报进程号，超时作废。
- **核对进程。** 进程号会被重复使用，所以还要核对命令行和启动时间。进程结束后，它占的资源自动收回。
- **调度模型服务。**
  - 一张卡同一时间只跑一个模型服务。
  - 用同一个模型的申请排在一起，共享一个服务。
  - 一个申请等满 30 分钟后，别的申请就不能再插到它前面。
  - 服务的所有者用完时，还有人在用就转交给别人，没人用了才停掉。
- **清单外的资源也能管。** 有人申请了清单里没有的资源，指挥中心会先把它加进清单，再审批。
- **记录写在磁盘上。** 账本整份替换写入，事件日志只追加。对话的上下文被压缩后，以文件里的记录为准。
- **命令加入、邀请加入。** 指挥中心可以命令某些对话必须加入，也可以只是邀请。对方加入后只回一句 `✅已加入`。
- **消息先走本机直连。** 桌面应用的对话间通道有发送上限（见"已知限制"），直连没有。

## 要求
- Claude 桌面应用（Code 标签页）。会用到对话间消息（`SendMessage`、`ListAgents`）、定时任务（`CronCreate`），以及桌面应用的会话工具（改会话名、查会话 ID）。
- 在 Windows 上实际用过。守则里也写了 Linux/macOS 下对应的命令，但没有实测。
- 要管显卡，需要 `nvidia-smi`。

## 安装
1. 下载本仓库，运行下面的命令（目标文件夹自己定）：
   ```bash
   python install.py ~/Desktop/00-Headquarters
   ```
   脚本会做三件事：
   - 把 `headquarters/` 里的文件复制到目标文件夹；
   - 把文件里的路径换成你机器上的实际路径；
   - 生成 `global-CLAUDE.snippet.md`。

   它不会改 `~/.claude` 里的任何文件。
2. 编辑目标文件夹里的 `resources.json`，登记三类东西：
   - 显卡：总显存、永久预留多少、用什么命令查占用；
   - 长期占用的端口；
   - 要加写锁的共享文件。

   格式参考 `resources.example.json`。
3. 把 `global-CLAUDE.snippet.md` 的内容追加到 `~/.claude/CLAUDE.md`。这样每个对话都知道：有指挥中心在岗时，用公共资源前要先申请。
4. 在 `~/.claude/settings.json` 里加上 `"crossSessionInbound": "accept"`。不加的话，权限模式不同的对话之间（例如 auto 和 bypass）消息会被扣住。
5. 已经开着的对话要重开，才会读到新的全局规则和设置。

## 使用
| 对哪个对话说 | 说什么 |
|---|---|
| 新开的一个对话 | `你是指挥中心` |
| 指挥中心 | `命令所有对话加入`，或 `邀请 <会话名> 加入` |
| 工作对话 | `加入最新的指挥中心`。不说也行，它要用公共资源时会自己加入 |
| 指挥中心 | `关闭指挥中心` |

加入以后，工作对话会自己申请、启动、回报、释放，指挥中心每 10 分钟巡查一次。想知道现在谁在用什么，直接问指挥中心。

## 目录
| 文件 | 内容 |
|---|---|
| `headquarters/CLAUDE.md` | 指挥中心的工作守则：上岗、关闭、调度与审批、巡查、记录、消息格式 |
| `headquarters/rules.md` | 给工作对话的规则：加入、申请、启动、释放、换指挥中心 |
| `headquarters/README.md` | 装好后放在指挥中心文件夹里的说明 |
| `headquarters/resources.example.json` | 资源清单的示例 |
| `headquarters/hq_registry.json` | 指挥中心的编号登记表，初始为空 |
| `global-CLAUDE.md` | 要追加到 `~/.claude/CLAUDE.md` 的全局规则模板 |
| `install.py` | 安装脚本 |
| `docs/messaging-notes.md` | 对话间消息的实测记录：两条通道、发送上限、同名对话、权限类别 |

运行起来以后：
- 指挥中心在自己的文件夹里生成 `hq-<编号>/state.json`（账本）和 `hq-<编号>/events.jsonl`（事件日志）；
- 每个工作对话在自己的工作目录里写 `hq_record-<会话名>.md`，记录它自己的申请。

## 已知限制
- **桌面通道有发送上限。** 按会话 ID 发的消息走桌面应用的通道。从用户上次在发送方对话里打字算起，最多只能这样发 10 条，定时任务触发的发送也不会让计数清零。官方文档没写这个上限，也没有设置能调高，见 [anthropics/claude-code#94000](https://github.com/anthropics/claude-code/issues/94000)。所以规则要求先按会话名直连发：直连没有这个上限，但对方必须正在运行。详见 `docs/messaging-notes.md`。
- **同名对话。** 按名字发，可能送到别的机器上同名的对话，所以规则要求核对返回结果。
- **只是约定，不能强制。** 指挥中心靠各对话遵守规则来协调，不会拦截进程。没加入的对话照样能用显卡。
- **子 agent 不能自己申请。** 子 agent 发出的消息用的是主对话的地址，回复也只送到主对话，所以要由主对话替它申请。

## 许可
本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE)：
- **非商业用途免费。** 个人学习、研究、实验、业余项目，以及学校、公益组织、公共研究机构、政府机构使用，都不用付费。
- **商业用途要另外取得授权。** 在公司或其他营利活动中使用，或者集成进商业产品、付费服务，都要先联系作者签商业授权，按约定支付授权费或收入分成。

商业授权请在本仓库提 Issue 联系作者。

Required Notice: Copyright 2026 bro789 (https://github.com/bro789)
