# 对话间消息：实测记录

2026 年 10 月在 Windows 上的 Claude 桌面应用（Code 标签页）里测得。Claude Code 更新后可能会变。

## 两条通道
| | 本机直连 | 桌面通道 |
|---|---|---|
| 谁来送 | Claude Code 自己。每个运行中的对话在本机开一个收信口，消息直接放进对方的收件箱 | 桌面应用，也就是管理所有对话标签页的那个程序。它把消息转进目标对话 |
| 怎么触发 | `SendMessage` 写对方的会话名，或 `名字 [ref]` | `SendMessage` 写对方的会话 ID（`local_` 开头）。返回结果里有 "Forwarded to Claude Desktop's session messaging" |
| 对方没在运行 | 找不到，报 "No agent named … is reachable" | 照样能送到，桌面应用会把对方启动起来（返回 "its turn has started on it"） |
| 发送上限 | 没有遇到 | 有，见下一节 |

## 桌面通道的发送上限
第 11 条被拒时的原话：

> Not delivered: this session has already messaged Claude Desktop sessions 10 times since your user last typed here, which looks like sessions messaging each other automatically. Paused until your user's next message in this session.

- 从用户上次在发送方对话里打字算起，最多 10 条。被拒的那几条也计数，后面的报错会写 11 次、12 次。
- 定时任务（CronCreate）触发的巡查、别的对话发来的消息，都不会让计数清零。只有用户在这个对话里打字才清零。GitHub 上有人反馈，要等这一轮结束之后再打字才算。
- 官方文档没写这个上限，也没有设置能调高。意思最接近的一句在桌面应用文档的 "Work across sessions" 一节：没人看着的对话（例如定时任务里）不能通过这条通道发消息。
- 已有的反馈：[anthropics/claude-code#94000](https://github.com/anthropics/claude-code/issues/94000)。

**直连不计数**，有两次实测：
1. 用户打字之后，一个对话共成功发出 12 条：按名字直连 1 条，经远程控制 1 条，按会话 ID 10 条。第 11 条会话 ID 消息被拒，报错说的是"10 次"。
2. 用户打一次字之后，按名字直连给同一个对话连发 15 条，没有一条被拒。对方回复 1 到 15 号全部收到。

## 直连要注意什么
- **对方必须正在运行。** 观察到的现象是：桌面应用重启后，一个对话如果没被打开过，也没收到过桌面通道的消息，就不在运行，按名字找不到它。
- **同名对话。** `ListAgents` 还会列出别的机器上（远程控制）和云端的对话。名字相同时，按名字可能送到别处，甚至送进一个离线对话的队列，等它上线才收到。所以：
  - 只认标着 `Claude Desktop session` 的那一行；
  - 有同名时写成 `名字 [ref]`；
  - 发完看返回写的是不是 "on this machine"。
- **ref 会变**，对话重启后可能不一样。要用当次 `ListAgents` 列出来的 ref。

## 权限类别
- 权限模式分两类：bypass 是一类，其余（auto、默认、plan 等）是另一类。跨类的消息默认被扣住，等接收方的用户批准。桌面应用里弹不出批准框，过 5 分钟消息就被丢掉。
- 在 `~/.claude/settings.json` 里设 `"crossSessionInbound": "accept"`，跨类的消息就直接放行。这个设置在对话启动时读取，改完要重开对话。
- 从手机远程控制开启的对话只能选到 auto，选不了 bypass。

## 其他
- 对话只在两次工具调用之间读新消息，不会打断正在运行的命令。空闲的对话收到消息，会开始新的一轮。
- 子 agent 发出的消息用的是主对话的地址，回复也只送到主对话。
- 返回 "success" 只说明消息进了对方的收件箱，不说明对方已经读到。
