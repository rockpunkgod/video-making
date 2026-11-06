# ANSWER

开明致学高考英语课程的 Skill 集合。以课程原始材料为准，把方法固化下来，供答疑、讲题和作文批改使用。

## 目录

| 目录 | 管什么 |
|---|---|
| [`gaokao-english/`](gaokao-english/) | 阅读、七选五、完形填空，以及这三类的方法问答和听力 |
| [`gaokao-grammar-fill/`](gaokao-grammar-fill/) | 语法填空 |
| [`gaokao-writing/`](gaokao-writing/) | 作文，即应用文与读后续写 |
| [`kaiming-english-qa/`](kaiming-english-qa/) | 课程知识问答，供前三个查证 |

按题型分工，一个题型只走一个技能，不重叠。

## 各自管什么

**`gaokao-english`** 管阅读、七选五、完形填空三类客观题，**并管这三类的方法问答**。模块包括 `router`（题型路由）、`delivery-contract`（学生交付合同）、三个题型模块（`reading-comprehension`、`seven-five`、`cloze`），以及 `listening`。学生问「三一致是什么」「定位怎么用」「这个方法怎么得出这个结论」这类方法本身的问题，由它答。方法只来自课程已核验的证据，遇到未覆盖、证据不足或题面不可辨认时停下并说明缺口，不用通用经验顶替。

**`gaokao-grammar-fill`** 管语法填空。含语法填空模块（按空位结构分路，无提示词与有提示词两条路线）、课程依据，以及客观题共用的定位卡与修稿工具。它沿用 2026-09-19 那份旧版技能，其余题型已由另外两个技能承接，所以目录里还留着当时共用的内部机制文件。

**`gaokao-writing`** 管应用文和读后续写。应用文含五审法、15 分五档评分和批改话术；读后续写含原文线索、十句五定法、25 分五档评分和批改话术。两类作文各有自己的评分表、结构诊断和反馈格式，不得混用，也不得把两类分数相加或换算。

**`kaiming-english-qa`** 管「课程怎么说的」。它把 78 份讲义转成可检索语料，每条带原文出处，适合核对某个方法是否为课程原名、课程在某处到底怎么讲。它自己不批改、不出分。

## 怎么搭配着用

按学生拿来的题目分派：

| 学生拿来 | 走哪个 |
|---|---|
| 阅读理解、七选五、完形填空 | `gaokao-english` |
| 问这三类的方法本身（是什么、怎么用、怎么得出某个结论） | `gaokao-english` |
| 听力 | `gaokao-english`，读 `references/listening.md` |
| 语法填空 | `gaokao-grammar-fill` |
| 应用文或读后续写的写作、批改 | `gaokao-writing` |
| 「课程是怎么讲这个方法的」「这个说法是不是课程原名」 | `kaiming-english-qa` |

三者是**互相指路**的关系，不是层层调用：学生拿来的不是本技能管的题型，说明这里不处理并指到对应技能，不用本技能的方法硬套。

方法问答与课程查证的分别：问**怎么用、怎么推出结论**走对应教学技能，它按课程方法实际演示一遍；问**课程到底有没有这么说、原话是什么**走 `kaiming-english-qa`，它给带出处的原文依据。

### 听力按答题与训练分开

课程音画核查已支持听力模块中的有限职责。解题三步保留精听练习条件；因病转低保是关注关系的助记，仍须核录音；倍速精听法、影子跟读法、盲听等按训练处理。各名称的入口、动作与边界见 `gaokao-english/references/listening.md`，不把可重听训练套成考试现场流程。

它的交付形态与其他题型一致：同一条微信答疑消息、同样的纯文本与标点要求、同样不排版不表演。没有录音时只能解释所给文本，不能声称已听辨实际发音。

## 三个 Agent

`agents/` 里是三份 Claude Code Agent 定义，把上面的分工落成可以直接调用的角色：

| 文件 | Agent 名 | 管什么 |
|---|---|---|
| [`agents/gaokao-objective.md`](agents/gaokao-objective.md) | `gaokao-objective` | 阅读、七选五、完形，以及这三类的方法问答和听力 |
| [`agents/gaokao-writing.md`](agents/gaokao-writing.md) | `gaokao-writing` | 应用文、读后续写 |
| [`agents/gaokao-grammar-fill.md`](agents/gaokao-grammar-fill.md) | `gaokao-grammar-fill` | 语法填空 |

三份里都写明了**该走哪个技能、不该碰哪个题型、拿错了往哪儿指**，所以分派不需要人来判断：学生拿来什么题，交给对应的 agent 即可。

## 怎么装

这些是 Claude Code / Codex 形式的 Skill，每个目录下有一份 `SKILL.md` 作为入口，`references/` 里是各模块。

装到本机时把目录放到 skills 目录下即可：

```
~/.claude/skills/gaokao-english
~/.claude/skills/gaokao-grammar-fill
~/.claude/skills/gaokao-writing
~/.claude/skills/kaiming-english-qa
```

Agent 定义放到 agents 目录：

```
~/.claude/agents/gaokao-objective.md
~/.claude/agents/gaokao-writing.md
~/.claude/agents/gaokao-grammar-fill.md
```

`gaokao-grammar-fill` 里带 `scripts/check_lesson.py`，客观题出稿前用它取源文定位卡、成稿后再带 `--draft` 修稿检查。这是内部环节，学生端看不到。

## 约定

- **课程优先**。方法名、判断顺序、证据要求以课程为准，不自创同名方法，不把知识清单当步骤讲。
- **交付是给学生看的一条消息**，不是报告、讲义或审计。纯文本，不用 Markdown 排版，方法融进实际动作里说。
- **证据不足就停**。说不清的地方如实说明缺口，不硬凑「完整思维链」，也不用常识补课。

## 说明

仓库放 Skill 本身。`kaiming-english-qa/references/originals/` 里另附 78 份课程讲义原件（docx / pdf），是问答语料的来源，体积较大，克隆时留意。蒸馏流水线和评测记录不在这里。

## 当前版本与核查资料

- 当前目录只保留新版 Skill；2026-10-18 按要求移除另存的旧版 ZIP 与说明，历史版本仍可通过 Git 提交追溯。
- [2026-10-13 课程术语核查资料快照](course-audits/2026-10-13/README.md)
- [2026-10-18 已核内容遗漏复核与补入记录](course-audits/2026-10-18/omission-review.md)
- [2026-10-30 正式 Skill 增量更新与遗漏复核](course-audits/2026-10-30/skill-update-review.md)
- [2026-10-30 回放轴定点续核与剩余边界](course-audits/2026-10-30/axis-followup-review.md)
- [2026-10-30 全缺口复核与同项状态更新](course-audits/2026-10-30/all-gaps-review.md)
- [2027届作文：按回放轴定位的增量更新](course-audits/2026-10-30/writing-2027-update.md)
