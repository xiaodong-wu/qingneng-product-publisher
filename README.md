# 清能社媒自动发布

为 **TSINO DYNATRON（清能）** 创建英文 B2B 产品推广图文的 Codex Skill。

先核对历史发布记录，再从[清能英文官网](https://en.tsino-dynatron.com/)随机或指定选择未发布产品，生成英文文案和一张四宫格配图，发布到[指定 Facebook 页面](https://www.facebook.com/profile.php?id=61587766500345)，验证结果后写入既定 Google 表格。

## 范围

- 仅发布 Facebook；不发布站内文章或 LinkedIn。
- 保留 `social-auto-upload` 五列表格，站内与 LinkedIn 两列固定填写 `不适用`。
- 按 Facebook 永久链接去重；表格回写失败不会触发重新发布。
- 选品前读取本地批次和完整表格记录，核实无法匹配的 Facebook 帖子；排除已发布及提交结果未明的产品。全部发过后停止，不自动重复。
- 提交前重新检查历史并记录本地提交占用，防止不同批次重复提交同一产品。
- 保留四条 emoji 特征、利益段落、CTA、官网链接和标签的原格式；根据产品事实调整表达，并比较近期五篇文案，避免只换型号的套话。
- 可选 AI 标签默认关闭；平台要求披露时如实处理。清理元数据或改文案均不能保证平台不会自行加标。
- 支持 `dry-run`、指定产品、随机选品和恢复用户指定的未完成批次。
- 发布前核对页面身份、权限、产品证据、文案和图片；提交结果不确定时先核查已发布内容。

本技能绑定清能的官网、Facebook 页面和表格。使用者需要相应账号权限；安装或查看技能不会自动发布，也不会创建定时任务。

## 安装

将本仓库放入 Codex 技能目录，例如：

```bash
git clone https://github.com/xiaodong-wu/qingneng-product-publisher.git \
  "$HOME/.codex/skills/qingneng-product-publisher"
```

如果目标目录已存在，请先检查已有安装，不要覆盖未保存的修改。

本地脚本需要 Python 3.10+ 和 Pillow：

```bash
python3 -m pip install -r requirements.txt
```

完整发布还需要 Codex 图片生成能力、可用的 Facebook 发布连接器或已登录 Chrome 会话，以及可访问目标表格的 Google Sheets 连接器。网站产品数据通过公开只读接口获取，不需要站内发布 API 密钥。

## 使用

在清能发布项目的聊天中输入：

```text
使用 $qingneng-product-publisher 随机选取一个产品并发布。
```

仅预演，不提交任何外部发布或表格写入：

```text
使用 $qingneng-product-publisher 执行 dry-run。
```

指定产品：

```text
使用 $qingneng-product-publisher 发布这个产品：https://en.tsino-dynatron.com/cp_xqy?pId=16
```

完整流程见 [SKILL.md](SKILL.md)。实际运行文件存放在技能目录之外，保留 manifest、产品证据、选品记录、素材与核验结果。

## 本地验证

```bash
python3 scripts/test_workflow.py
```

测试使用临时目录和模拟证据，不发布帖子、不写入 Google 表格。覆盖历史去重、未决提交、目录用尽、表格补录、原文案格式、重复文案和 AI 披露规则等行为。这些检查不代表已完成 Facebook 登录、图片生成、真实发布或 Google 表格写入测试。

## 文件

- `SKILL.md`：技能入口。
- `agents/openai.yaml`：Codex 展示名称与默认调用提示。
- `references/`：产品来源、文案图片规范、发布、表格回写和证据格式。
- `scripts/`：历史核对与排除、公开产品抓取、图片优化、批次校验、状态记录、完成检查及离线测试。

仓库不包含账号凭据、浏览器会话、运行记录或客户数据。
