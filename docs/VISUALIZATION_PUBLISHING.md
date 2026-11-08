# HTML 可视化发布：新 Codex 窗口操作手册

当前有效流程，2026-11-07。正常发布直接执行下方命令，不需要重新搭建服务器或寻找认证方式。
用户已持续授权发布本仓库新生成的 HTML；上传后必须在回复中给出完整网址。

## 页面内容：中文与英文两种选择

所有新制作或重新导出的 HTML，模型输出、prompt（提示词）、原始任务指令、理由说明等
英文自然语言内容均须完整翻译为中文。页面提供明确的“中文 / English”切换，默认中文；
切换须覆盖正文和详情面板，不能仅翻译界面标题、按钮，或用中文摘要代替完整翻译。

每条中文译文关联对应英文原文，英文原文完整保留。忠实保留原答的否定、数量、方向、
不确定性及错误，不借翻译纠正模型结论。原始 JSON、请求和响应保留原始字段与内容，
其自然语言内容另有中文展示；ID、路径、数值、代码和协议枚举保持原值，可附中文释义。
翻译只影响可视化，不改实际实验输入、发送的 prompt、原始响应、哈希或评分依据。

本地页面检查时验证：两种语言均可选，任务/帧/回答对应关系不变，正文无漏译。
在线拆分与上传脚本不会自动翻译；须在生成可视化内容时完成双语数据和切换功能，再执行发布流程。

## 标准发布：只改源文件和版本名

在仓库根目录执行。源文件使用本轮已经导出、检查过的离线 HTML。
`VIS_RELEASE` 每次换成新名称，建议 `<实验>_<方法版本>_<运行编号>_web_<日期>_<序号>`，只用英文、数字、下划线、点或连字符。
下面的源文件是已完成的示例；发布其他实验时替换它，不要重跑模型来生成示例。

```bash
VIS_SOURCE='outputs/crossing_checkpoint/lite_v001/run_20261107_01/exports/final/crossing_lite_review.html'
VIS_RELEASE='crossing_lite_v001_run_20261107_01_web_20261107_02'
VIS_DEST="outputs/visualization_publishing/$VIS_RELEASE"

python3 -B - "$VIS_SOURCE" "$VIS_DEST" "$VIS_RELEASE" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

source, destination, release = sys.argv[1:]
# 已有目录会被拒绝；拆分失败立即停止，不继续发布。
subprocess.run([
    sys.executable, '-B', 'scripts/prepare_online_visualization.py',
    '--html', source, '--destination', destination,
], check=True)
folder = Path(destination)
manifest = json.loads((folder / 'online_manifest.json').read_text())
# 在进程内传入完整资源清单，避免几千个文件逐个SSH，也避免shell参数长度限制。
sys.path.insert(0, str(Path('scripts').resolve()))
import publish_visualization
sys.argv = ['publish_visualization', '--html', str(folder / manifest['html']), '--name', release]
for asset in manifest['assets']:
    sys.argv.extend(['--asset', asset])
publish_visualization.main()
PY
```

该命令依次完成：

1. 新建在线导出目录，将内嵌图片、字体提取到 `assets/`，保存 `online_manifest.json`；原离线文件保持原样。
2. 自动读取仓库中的服务器密码，直接 SSH/SCP 连接服务器。
3. 将 HTML 和清单内全部资源打包后一次上传；远端逐个校验 SHA256，通过后开放目录读取。
4. 对 HTML 入口做公网 HEAD 检查，确认 HTTP 200、`text/html` 和响应中提供的文件大小。
5. 打印 `Publication record: .../publication.json` 及最终网址。

**必须把全部资源一起发布。** 不能只上传拆分后的 HTML，否则图片必然缺失。
原单文件曾达 62 MiB，初始化脚本在全部媒体之后，下载未结束时只显示框架；在线入口必须使用拆分版。
此拆分器适用于图片/字体内嵌的现有页面。原 HTML 已有外部 JS、CSS、JSON、图片、视频时，
须先在新导出目录整理这些相对路径依赖，并用下节的 `--asset` 补齐；拆分器不会自动发现或复制原有外部依赖。
若更换页面模板，须确认其代码能使用相对图片 URL，而非强制要求 `data:image/...`。

## 已生成在线版：直接发布或重验

如果已有 `online_manifest.json`，无需再次拆分。使用上段 Python 中从 `folder = Path(destination)`
开始的部分，令 `destination` 为已有在线目录，`release` 为本次新版本名即可。

文件较少或已经手工整理的页面，也可使用基础入口（每个必要资源分别传 `--asset`）：

```bash
python3 -B scripts/publish_visualization.py \
  --html outputs/<在线目录>/review.html \
  --name <新版本名> \
  --asset review.js \
  --asset data.json \
  --asset images/frame01.webp
```

资源路径相对于 HTML 所在目录，保留相对目录结构；不传无关文件、目录或凭据文件。
大量资源始终使用清单展开的 Python 写法；发布脚本会自动打包，不能逐个手工 scp。

若上传成功，仅公网检查失败，用相同的 HTML、版本名和完整资源清单，加 `--verify-only`。
上段 Python 中可在调用 `publish_visualization.main()` 前加：

```python
sys.argv.append('--verify-only')
```

该选项只重验已存在的远端文件，不重新上传。若改过 HTML 或资源，必须使用新的版本名。
`--dry-run` 只检查本地清单并打印计划；不联网，也不代表已发布。

## 交付与记录：通过后立即提供链接

- 发布进程退出码必须为 0；其打印的记录文件应为 `phase: published`、`remote_sha256_verified: true`，HTML 条目有 `http_status: 200`。
- 默认不从公网重新下载全量文件。资源完整性由全部远端 SHA256 保证；HEAD 不证明页面交互正确。
- 本地按该页面模板检查数据数量、图片、双进度条及必要交互。仅重新发布已验证且未改动的同一在线版时，复用已有页面验证记录。
- 需要在线排障时，仅对入口、代表性图片和交互做一次有时间上限的浏览器检查。默认直连，页面导航上限 45 秒；超时记录实际原因，不反复全量下载。
- 在具体实验/导出 README 登记源 HTML、在线目录、版本名、最终 URL、发布时间、发布记录路径及实际验证范围。不要将“HEAD 通过”写成“在线浏览器通过”。
- 最后回复用户可点击的完整 URL。正常发布到此结束，不再扩大验证或重启实验。

地址规则：`http://134.175.18.101/vln/<版本名>/<HTML文件名>`。
本地发布证据位于 `outputs/visualization_publishing/publish_<UTC时间>/publication.json`。
同一方法新导出、新版本、新修订均用新的目录/网址；不覆盖、删除旧版本。需要查看旧版时，直接使用旧网址。

## 服务器固定信息：已配置，无需重复部署

| 项目 | 已验证配置 |
| --- | --- |
| SSH | `ssh root@134.175.18.101`，默认 22 端口，直连 |
| 公网入口 | `http://134.175.18.101/vln/`，使用具体文件地址，根目录没有列表页 |
| 远端文件根目录 | `/www/wwwroot/vln_2026_autumn` |
| 网站目录映射 | `/www/server/nginx/html/vln` 软链接到上述根目录 |
| Web 服务 | 已有宝塔 Nginx，`/www/server/nginx/sbin/nginx`，HTTP 80 |
| Nginx 主配置 | `/www/server/nginx/conf/nginx.conf`；当前默认80端口主机在 `phpfpm_status.conf` |
| 发布配置 | [core/visualization_publish.json](../core/visualization_publish.json)，含服务器公开主机密钥 |
| 认证文件 | `core/visualization_publish_credentials.json`，用户明确要求存入仓库，权限0600 |
| 在线版生成 | [scripts/prepare_online_visualization.py](../scripts/prepare_online_visualization.py) |
| 上传及检查 | [scripts/publish_visualization.py](../scripts/publish_visualization.py) |

密码由脚本的临时 SSH askpass 助手读取，无需手工输入、再次索取或安装 sshpass。
密码不能复制到公开 HTML、资源清单、URL 或日志。认证文件不属于要上传的静态资源。
既有 SSH agent/密钥也可使用；`--identity-file` 指定已有密钥，`--ssh-control-path` 复用已有会话。

7892 是可选 HTTP 代理，不是 SSH 上传端口。**默认不指定代理，直接发布。**
仅当确需使用用户代理时加 `--user-proxy`；它失败后自动绕过并直连，不使用他人的代理。
`--full-http-check` 会完整下载，只有用户明确要求或诊断确需时使用。

日常操作只向项目的新版本目录写入静态文件。不安装服务、不修改防火墙或其他网站、不重启 Nginx，
也不启动临时 `python -m http.server` 代替已有站点。服务器配置发生实际变化时才重新核查路径映射。

## 常见故障：按现象处理

| 现象 | 固定处理 |
| --- | --- |
| 本地目标目录或远端版本已存在 | 保留原目录，换一个新版本名；仅校验原版本才用 `--verify-only` |
| 认证失败 | 检查仓库认证文件是否存在、账号/IP是否与配置一致；不要把密码打印到日志 |
| SSH 主机密钥变化 | 核实服务器身份及实际变更后更新配置，不关闭密钥核验 |
| 7892 不可用 | 不指定代理；SSH 本来就直连，HTTP 验证可自动回退直连 |
| 已上传，HEAD 超时 | 保留当前版本与失败记录，执行一次 `--verify-only`；继续失败则报告网络问题，不重复上传 |
| 页面只有框架、列表为空 | 先确认交付的是在线拆分版；再看浏览器脚本错误和数据请求，不能只凭 HTTP 200 判断正常 |
| 图片/样式/数据缺失 | 对照资源清单和相对URL，核对404及漏传文件；修复后发布新版本 |
| 页面数据本身不全 | 对照本轮原始结果与本地浏览器检查；不要为修复展示擅自重跑模型 |
| 发布中断，留下部分文件 | 保留失败记录和版本目录，修复后使用新版本名；不对服务器做模糊匹配清理 |

## 已验证案例与历史证据

[三帧 Crossing 在线版](http://134.175.18.101/vln/crossing_lite_v001_online_20261107_01/crossing_lite_review.html)：
HTML 3,799,721字节、2600个资源，全部远端哈希通过。本地浏览器通过30条轨迹、2589帧、156位置及复核导出；
公网浏览器直连检查首末轨迹图片、双进度条通过，零JS错误，约19.9秒。

- 在线文件/清单/浏览器证据：`outputs/visualization_publishing/online_20261107_01/`。
- 发布记录：`outputs/visualization_publishing/publish_20261107_072020_383244/publication.json`。
- 初次接入与历史超时记录：`outputs/visualization_publishing/setup_20261107_01/`。
- 整理前旧版说明：`outputs/visualization_publishing/documentation_20261107_01/before/docs/VISUALIZATION_PUBLISHING.md`。

历史的62 MiB单文件地址只保留追溯，不再作为日常交付入口。新窗口优先执行本文当前流程。
