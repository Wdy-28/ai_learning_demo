# 项目长期记忆（个人工作台）

- 用户偏好：一次只问一个问题；涉及视觉改动先给效果看再改；方案先确认再执行。
- 项目主目录：`D:\ai-learning\code\personal-dashboard\`（用户要求放 D 盘项目库，已并入 `ai-learning` 仓库 / `Wdy-28/ai_learning_demo`）；单文件离线 `index.html` + `favicon.png`，绿色「薄荷青柠」夏日清凉风；原 `Wdy-28/personal-dashboard` 独立仓库暂停使用，C 盘会话目录仅留历史。
- 项目内容只存 D 盘：C 盘会话目录只剩 WorkBuddy 必需的 `.workbuddy` 元数据；旧项目副本、旧 `.git` 与临时验收文件已归档到 `D:\ai-learning\.archive\personal-dashboard-c-copy\`，后续所有项目读写使用 D 盘绝对路径。
- 课表来源：桂林理工大学老版正方（`jw.glut.edu.cn/academic/affairLogin.do`）。当前页面数据来自用户提供的第 12 周课表截图，12 节作息（雁山校区）：08:30/09:20/10:25/11:15/14:30/15:20/16:25/17:15/18:30/19:20/20:15/21:05，每节 45 分钟。
- **课程固定事实：军事理论在周三（第 11-12 节，教师范志祥）。用户明确要求记住，不要按截图误读成周五。**
- 教师姓名核对：C 语言程序设计（二）为「杨呈永」（用户确认）；其余按截图：李明、史伟、侯彦恒、滕丽媛、邓小芹、韦兴、张露萍、范志祥。
- 课表双数据入口：`courses.json`（Actions / 远端）+ `courses.js`（`window.COURSE_SYNC=...`，本地 file:// 可用）。页面优先本地 JS，再远程 JSON，再缓存，最后内置数据。
- 同步链路：工作流在 `D:\ai-learning\.github\workflows\sync-schedule.yml`，只保留 `workflow_dispatch` 手动触发；脚本/产物路径已加 `code/personal-dashboard/` 前缀；Secrets 需在 `ai_learning_demo` 仓库配置；真实抓取尚未验证，不要声称已跑通。
- 页面打开策略：每次打开 `index.html` 先读同目录 `courses.js`（D 盘最新本地数据）并写入本机缓存；远端 raw 仅作回退，地址已改为 `ai_learning_demo/main/code/personal-dashboard/courses.json`。
- 数据结构：课程块含 `day`、`period`（起始节）、`end`（结束节）、`title`、`location`、`teacher`；`end` 允许跨节显示。
- 课表显示：相邻重复课合并为一个跨行大色块；所有课程块统一薄荷绿（#A8E6CF）；左侧节次文字按第 1-12 节由浅到深，起止时间仍在节次下方。
- 截图导入：页面有上传入口，tesseract.js 7.0.0 从 jsDelivr 按需加载，识别在本机浏览器完成；结果必须逐条核对后确认导入。真实截图实测约 16/18 条可用，课程名/教师仍有 OCR 错字，不要宣称一键准确。军事理论强制周三 11-12。
