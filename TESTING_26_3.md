# owo-lib 26.3 升级后：实机测试指南

> 配套文档：`UPGRADE_26_3.md`
> 前提：已完成 `gradle build`（含 `validateAccessWidener`）与 `compileTestmodJava`

---

## 0. 一句话版本

```powershell
cd C:\Users\Administrator\Desktop\mod\owo-lib-0.13.1-26.2
$env:JAVA_HOME='C:\Program Files\Zulu\zulu-26'
& 'C:\Users\Administrator\.gradle\wrapper\dists\gradle-9.7.1-bin\brhrg0o7dy6fa4wpk3ipunw7x\gradle-9.7.1\bin\gradle.bat' runTestmodClient --no-daemon --console=plain
```

> 用已解压的 gradle 9.7.1 二进制，避开 wrapper 下载超时（`gradlew.bat` 会去下分发包）。
> 任务名是 `runTestmodClient`（build.gradle 里 `runs { testmodClient { client() } }` 定义的名字）。

---

## 0.5 ⚠️ 三个最常见的"假故障"

**① 命令在主菜单里不存在 —— 这是正常的**

Fabric 的客户端命令**只在进世界后才注册**。
`fabric-command-api-v2` 的 `ClientPacketListenerMixin` 仅在
`handleLogin` / `handleCommands`（收到 `ClientboundLoginPacket`）时触发
`ClientCommandRegistrationCallback.EVENT`。

→ **必须先进世界，再按 `T` 输入 `/`。**

**② uωu 页签找不到 —— 位置不对**

它不是原版创造模式页签，而是 owo 的 `OwoItemGroup`
（testmod 注册为 `uwu:four_tab_group`），在创造模式物品栏里作为**独立分组**显示。
→ **需要进世界 + 创造模式 + 横向翻页签。**

**③ 日志停在初始化那行不动 —— 不是卡死**

`latest.log` 只在有事件时写入。窗口开着不动 = 你没操作。
判断客户端是否活着，看进程：`Get-Process java | Where-Object { $_.MainWindowTitle -match 'Minecraft' }`

**④ 看到 `Couldn't parse UI model xxx.xml` 别慌**

testmod 里 `parse_fail.xml` 是**故意写坏**的容错测试，
owo 正确捕获了异常且游戏没崩 —— 这是**期望行为**。

---

## 1. 分层测试：从最轻到最重

### 第 0 层：启动即崩不崩（30 秒）

启动 `runTestmodClient`,**只要进到主菜单**就算过了这一层。

这一层专门抓 **mixin 应用失败**。26.3 移植里最容易翻车的就是 mixin 目标签名变了
（`@Inject` 的 `method=` 指向的方法不存在/改参数 → 加载期直接崩）。

如果崩了，日志里会有这样的行：

```
Mixin apply failed ... was not found in ...
InjectionError: Critical injection failure
```

**怎么找日志**：运行目录 `run/logs/latest.log`,或者看控制台输出。

**日志在哪**：`run/` 目录（loom 自动建），`run/logs/latest.log`。

关键判断：
- 能进主菜单 → mixin 至少没崩
- 崩在 `MixinApplyError` → 那个 mixin 的目标在 26.3 变了，要改 `@Inject`/`@At` 的签名

### 第 1 层：owo 配置界面（2 分钟）

> ### ⚠️ 必须先进世界！
>
> **Fabric 的客户端命令只在收到登录包时才注册。**
> `fabric-command-api-v2` 的 `ClientPacketListenerMixin` 只在
> `handleLogin` / `handleCommands`（即收到 `ClientboundLoginPacket`）时
> 触发 `ClientCommandRegistrationCallback.EVENT`。
>
> **所以在主菜单里，`/owo-config`、`/owo-hud-inspect` 这些命令压根不存在。**
> 这不是 owo 的 bug，是 Fabric 的既定设计。
>
> 正确顺序：**进世界 → 按 `T` → 输入 `/` → 命令才出现。**

**A. 命令**（推荐，最快）
```
/owo-config
```
Tab 补全选 `uwu`（testmod 的测试配置）。

**B. ModMenu**
ModMenu 里 owo 是个 library，一般不出现在模组列表，但 testmod 注册了 `uwu` 配置，
可以走 `/owo-config uwu`。

**C. testmod 物品**（需要先进世界，见第 2 层）
创造模式物品栏 → 找 **uωu** 物品栏页签 → 拿 **Screen Shard** → 右键。

**要检查什么**：

| 检查点 | 期望 | 出问题说明 |
|---|---|---|
| 界面能打开 | 面板正常渲染 | 渲染层（renderpearl）移植有问题 |
| 文字清晰无重叠 | 字体正确 | `Font` 相关 mixin 挂了 |
| 按钮 hover 有高亮 | 交互正常 | 渲染状态（`GlStateManager` 移除后）出问题 |
| 滚动条能拖 | 容器裁剪正常 | `ScissorStack` / 裁剪相关 |
| tooltip 悬浮显示 | 提示正常 | tooltip 定位 mixin 挂了 |
| **关掉界面后能回到游戏** | 不卡死 | `setScreen` → `gui.setScreen` 迁移有问题 |
| 调整选项后重开界面,值还在 | 配置持久化正常 | 序列化（endec）有问题 |

> ⚠️ **"关掉界面后能回到游戏"这条特别重要**。26.3 里 `Minecraft.setScreenAndShow()` 被废弃成
> `Minecraft.gui.setScreen()`，如果哪里漏改了，症状就是**切界面后画面卡住不动**
> （不渲染世界但也不崩）。这是本次迁移最容易漏的坑。

> 💡 **uωu 页签在哪**：它是 owo 自己的 `OwoItemGroup`（testmod 注册为
> `uwu:four_tab_group`），在创造模式物品栏里作为一个**独立分组**显示，
> 标签是 "uωu"，不是原版创造模式页签。需要**先进世界 + 创造模式**才看得到。

### 第 2 层：testmod 界面全集（10 分钟）

testmod 有个「Available screens」选择界面，内含 6 个 owo UI 演示。

**进入方式**：创造模式物品栏 → **uωu** 页签 → **Screen Shard** → **Shift + 右键**
（普通右键开的是容器界面，不是这个选择界面）。

进去后逐个点：

| 按钮 | 测什么 |
|---|---|
| `code demo` | 纯代码构建的 UI |
| `xml demo` | XML 解析的 UI（`UIParsing` 改了） |
| `code config` | 代码式配置界面 |
| `xml config` | XML 式配置界面 |
| `optimization test` | 大量组件时的性能 |
| `focus cycle test` | 焦点循环（Tab 键导航） |
| `expand gap test` | 布局间距计算 |

XML 界面对应的资源在 `src/testmod/resources/assets/uwu/owo_ui/`，
一共 7 个 xml: `config.xml`、`expand_gap_test.xml`、`focus_cycle_test.xml`、
`parse_fail.xml`、`smol_components.xml`、`test_element_one.xml`、`test_element_two.xml`。

> `parse_fail.xml` 是**故意写坏**的,用来测容错——它应该报一个友好的解析错误,
> 而不是崩游戏。如果它导致崩溃,说明 26.3 的 XML 解析异常处理没迁好。

### 第 3 层：braid 独立窗口（10 分钟，**风险最高**）

braid 是 owo 的**独立原生窗口**系统，26.3 把窗口/输入从 GLFW 全换成了 SDL3，
还改了渲染后端（Vulkan/OpenGL 各自的 swapchain）。这是本次移植最重的部分。

**进入方式**：创造模式物品栏 → **uωu** 页签 → **Braid (chyz tried)** 物品 → 右键。

打开后你会看到一个**独立的原生窗口**（不是游戏内 GUI）。里面还有 28 个测试页签：

```
Amogus          GayAmogus       FunnyDragText   Bikeshed
AnimationsTest  AutomaticAnimationTest          BurningChyzTest
ContributorsTest  CounterTest   CyclingTest     DragArenaTest
FlexTest        GridsTest       InputTest       KdlWidgetsTest
NavigatorTest   OptimizationTest  OverlayTest   ScrollTest
SharedStateTest  SliderTest    SpinnyGhastTest SplitPaneTest
StacksTest      TextInputTest   TextTest       VanillaTest
```

**优先级最高的三项**（对应本次迁移的核心变更）：

**① `InputTest` — SDL3 输入系统**
- 点按钮、拖滑块、键盘输入文字
- 测左右键分别响应（26.3 SDL 鼠标键值 1/3/2 的映射,PR 里专门修过这个 bug）
- 测修饰键（Shift/Ctrl/Alt）组合
- **重点**：这个测试在迁移前是**失败**的（PR500 作者自述 "The left-GUI case failed before the correction because EventBinding checked the right key twice"）。如果现在左右键行为反了,说明 SDL 键值映射又出问题了

**② `TextInputTest` — 文本输入**
- 输入文字、选中文本、复制粘贴
- 26.3 换 SDL 后 IME 和文本输入事件模型变了

**③ `VanillaTest` — 原生控件互操作**
- owo 窗口里嵌原版控件
- 原版控件在 SDL 环境下是否还能正常响应

**窗口级操作**（SDL 迁移的核心）：

| 操作 | 期望 |
|---|---|
| 拖动窗口边缘 | 尺寸变化,内容跟着重绘（resize 事件） |
| 关闭窗口 | 窗口正常消失,**游戏不崩、不卡** |
| 再开一个 | 不泄漏 swapchain |
| 反复开关 5 次 | 内存不涨,窗口不残留 |
| 最小化再还原 | 正常恢复 |

> ⚠️ **反复开关窗口**是必测项。26.3 的 `BraidWindow` 需要显式 dispose surface/renderer
> （PR 里加了 `disposed` 标志和 `SDL_EventFilter`）,如果清理不干净,
> 症状是开几次之后游戏卡死或显存爆掉。

### 第 4 层：自定义 shader（5 分钟）

owo 有 3 个自定义 shader:blur（模糊）、spectrum（光谱）、渐变。它们在 26.3
从 `#version 150` 升到了 `#version 330` + `GL_ARB_separate_shader_objects`,
并且 `#moj_import` 改成了 `#include`。

**怎么触发**：
- 配置界面里的模糊/背景模糊效果
- `BraidDisplay` 展示方块（创造模式 → **Braid Display** 方块）
- 某些界面的渐变背景

**要检查**：模糊效果有没有变成**纯黑/纯白/花屏**。
shader 编译失败在 MC 里通常是静默降级（效果消失）而不是崩溃,所以要**肉眼确认效果还在**。

### 第 5 层：配方系统（5 分钟）

26.3 把配方改成了**数据包注册表**,owo 的 `owo:remainders` 扩展 hook 从
`SimpleJsonResourceReloadListener` 挪到了 `RegistryLoadTask$PendingRegistration`。

**怎么测**：
1. 创造模式拿一个有**合成剩余物**的物品（比如工作台或熔炉）
2. 看合成台界面,合成后剩余物是否正确留在槽里

**更直接的测法**：用 testmod 的配方文件
`src/testmod/resources/data/uwu/recipe/uwu_shaped_recipe.json5`。

> ⚠️ **这个文件在 PR501 里被删掉了**,因为它引用的配方类型已被注释掉,
> 而 26.3 里未注册的配方类型会**在加载期致命报错**（26.2 只是静默失败）。
> 所以现在的状态是「已删除」,这是正确的。

**你该测的**是第三方模组的自定义配方 + owo 的 remainders 扩展还能不能配合。
如果只跑 testmod,这块测不出来——需要装一个带自定义配方的模组。

### 第 6 层：命令行功能

这些命令**没有 `/owo` 前缀**,是直接顶层的:

```
/owo-config <id>          # 打开配置界面（Tab 补全）
/owo-hud-inspect          # HUD 检查器
/owo-ui-set-reload-path <model-id>   # UI 热重载路径（Tab 补全已加载的 model）
/renderdoc                # RenderDoc 集成（仅当 RenderDoc 可用时才注册）
/renderdoc comment <capture_index> <comment>
/logger <level>           # 全局日志级别
/query-poi <poi_type> <radius>
/dumpfield <field_name>
/dumpdata item|block|entity
/make-loot-container
/heal
/cca-data
```

**`/renderdoc`** 值得单独试——它涉及 RenderDoc 的原生 hook,
在 26.3 换 SDL 之后可能需要重新适配。注意它只在 `RenderDoc.isAvailable()` 时才注册,
所以如果命令不存在,说明当前没检测到 RenderDoc,这是正常的。

---

## 7. 命令速查（找错时用）

| 命令 | 用途 |
|---|---|
| `/owo-config` | 打开 owo 配置界面 |
| `/owo-hud-inspect` | HUD 检查器 |
| `/owo-ui-set-reload-path` | UI 热重载（改 xml 后即时生效） |
| `/logger <level>` | 调日志级别,查问题时可开到 debug |
| `/dumpdata item` | 转储物品数据 |
| `/renderdoc` | RenderDoc 抓帧 |

> **调日志级别**很有用:出问题时先 `/logger debug`,日志里会多出大量细节,
> 配合 `latest.log` 更容易定位 mixin / 渲染问题。

---

## 2. 日志在哪、怎么查

运行目录是项目下的 `run/`:

| 文件 | 内容 |
|---|---|
| `run/logs/latest.log` | **主日志**,mixin 错误、shader 错误都在这 |
| `run/crash-reports/` | 崩溃报告 |
| `run/screenshots/` | 截图 |

**快速筛 mixin 错误**：

```powershell
Select-String -Path 'C:\Users\Administrator\Desktop\mod\owo-lib-0.13.1-26.2\run\logs\latest.log' -Pattern 'Mixin|mixin|Failed|ERROR|WARN' | Select-Object -First 40
```

**重点关注这几类**:
- `Mixin apply failed` / `was not found in` → mixin 目标在 26.3 变了
- `InjectionError: Critical injection failure` → 注入点签名不匹配
- `Shader compilation failed` / `Could not compile` → GLSL 迁移没做对
- `InvalidMixinException` → accesswidener 与实际类不匹配

---

## 3. Vulkan vs OpenGL

26.3 的渲染层换成 renderpearl 后,**Vulkan 和 OpenGL 是两套独立代码路径**
（braid 窗口要分别建 swapchain）。

**建议两个都测**：

在 `run/options.txt` 里加/改：
```
graphicsBackend:opengl
```
或
```
graphicsBackend:vulkan
```

> ⚠️ 这台机器的 Vulkan 运行时**未经验证**。PR500 作者明确写了
> "the Vulkan API path compiles, but Vulkan runtime behavior has not yet been verified"。
> 如果你的显卡驱动对 Vulkan 支持不好,OpenGL 路径测通了也先别急着下结论。

---

## 4. 优先级建议

时间有限的话,按这个顺序:

1. **启动不崩**（0.5 分钟）—— 抓 mixin 目标失配
2. **配置界面开关一次**（2 分钟）—— 抓渲染层 + `gui.setScreen` 漏改
3. **braid 窗口开关 3 次**（3 分钟）—— 抓 SDL 窗口生命周期
4. **`InputTest` 左右键**（2 分钟）—— 抓 SDL 键值映射
5. **shader 模糊效果**（2 分钟）—— 抓 GLSL 迁移
6. 其余界面/功能（可选）

---

## 5. 出问题时的定位思路

| 症状 | 大概率原因 | 去哪看 |
|---|---|---|
| 启动就崩,mixin 报错 | 26.3 改了目标方法签名 | `latest.log` 的 `Mixin apply failed` 行 → 改对应 `@Inject`/`@At` |
| 界面能开但不渲染/黑屏 | renderpearl 管线或状态管理 | `GlStateManager` 移除后的状态残留 |
| 切界面后卡住不动 | 漏改 `setScreenAndShow` → `gui.setScreen` | 全局搜 `setScreenAndShow` |
| braid 窗口开不出来 | SDL 窗口创建失败 | `latest.log` 里 SDL 相关异常 |
| braid 窗口开几次后崩 | surface/renderer 没 dispose | `BraidWindow.dispose` 路径 |
| 鼠标左右键行为反了 | SDL 键值 1/3/2 映射错 | `EventBinding` / `CursorController` |
| 模糊效果消失 | GLSL 版本或 `#include` 语法 | 3 个 `.fsh`/`.vsh` 文件 |
| 配方加载崩游戏 | 配方类型未注册 | 数据包注册表（26.3 新机制） |

---

## 6. 上游参考

| 资源 | 地址 |
|---|---|
| PR #501（本次移植基线） | https://github.com/wisp-forest/owo-lib/pull/501 |
| PR #500（另一条路线,含静态审计） | https://github.com/wisp-forest/owo-lib/pull/500 |
| PR #500 的构建文档 | `PORTING_26_3.md` |

PR #501 作者的实测环境是 **Linux + Wayland + Nvidia,OpenGL 与 Vulkan 都跑过**。
你在 Windows 上遇到的问题如果和作者描述的不一致,大概率是环境差异而非移植缺陷。
