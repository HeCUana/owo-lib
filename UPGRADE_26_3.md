# owo-lib 0.13.1：Minecraft 26.2 → 26.3 升级分析

> 分析对象：`C:\Users\Administrator\Desktop\mod\owo-lib-0.13.1-26.2`
> 基线确认：本目录 914 个文件与上游 `wisp-forest/owo-lib` 分支 `26.2` HEAD (`9c9772e1728dd4c5f1178ce955d1b3747f53493a`) 逐 blob 校验一致
> （仅 `braid-reload-agent/gradlew.bat` 存在行尾差异，不影响编译）

---

## 零、已完成的移植（2026-11-09）

本目录**已经升级到 26.3 并通过完整构建**。实施方式：以上游 PR #501 的移植 diff 为基底
（`git apply` 全量落地，exit 0），再按本地网络环境调整依赖源。

实际执行并验证通过：

| 验证项 | 结果 |
|---|---|
| `gradle compileJava` | BUILD SUCCESSFUL |
| `gradle build`（含 `validateAccessWidener`） | BUILD SUCCESSFUL |
| `gradle compileTestmodJava`（testmod 92 个文件） | BUILD SUCCESSFUL |
| `gradle runTestmodServer`（无 GUI） | **服务端成功启动**：`Done (3.685s)!` |
| 静态 mixin 审计（`tools/audit_mixins_263.py`） | **102 个 mixin，0 问题** |
| 产物 | `build/libs/owo-lib-0.13.1+26.3.jar`（2.2 MB，1298 entries） |
| GLFW 残留引用 | 0 |
| mixin 配置一致性 | 102 条目全部有对应源文件 |

本次在 PR #501 之外额外做的三类本地适配：

1. **EMI 依赖源替换**（必需，否则构建无法开始）
   `maven.terraformersmc.com` 会 302 重定向到 `repo.sleeping.town`，该域名在本地网络超时。
   改为 Modrinth Maven 坐标 `maven.modrinth:emi:1.1.18+1.21.1+fabric`
   （已核验该 jar 内含 `dev/emi/emi/api/**` 共 477 个条目，类名一致）。
2. **Gradle 版本改为 9.7.1**
   原定 9.8.0 会触发 130 MB 下载且本机连接超时；9.7.1 已在 `~/.gradle/wrapper/dists`
   完整解压，可离线使用。build.gradle 的 Loom 保持 PR501 的 `1.18-SNAPSHOT`（实际解析为 1.18.4）。
3. **修复 testmod 的服务端崩溃**（PR #501 遗漏，见下节）

### 修复：testmod 在服务端直接崩溃

PR #501 移植后，**服务端启动即崩**：

```
java.lang.BootstrapMethodError: Cannot load class net.minecraft.client.gui.screens.Screen
    in environment type SERVER
    at io.wispforest.uwu.items.UwuItems.<clinit>(UwuItems.java:20)
```

**根因**：Fabric 的 `@Environment(EnvType.CLIENT)` 环境剥离器会**整体移除被标注的方法**，
所以客户端方法体里的引用不会导致问题；但**字段和静态初始化块不会被剥离**。

`BraidSamplesItem` / `UwuBraidItem` 里存在客户端类型的成员（`BraidScreen.Settings` 静态字段、
`Minecraft` 引用），类初始化时 JVM 就会解析这些客户端类 → 服务端环境直接抛错。

**修法**（本次采用）：

- 新增顶层类 `io.wispforest.owo.braid.core.BraidScreenSettings`
  （原本是 `BraidScreen` 的嵌套类，嵌套在客户端类里同样会拖入 `Screen`）。
  `BraidScreen.Settings` 保留为 `@Deprecated` 兼容别名。
- 把客户端逻辑拆到独立类：`BraidSamplesClient`、`UwuBraidClient`，
  物品类只留一个 `@Environment(EnvType.CLIENT)` 的转发方法。
- `UwuScreenShardItem` 的 `use()` **取消**了 `@Environment` 标注
  ——原来整个方法被剥离，导致**服务端开菜单的逻辑也一起没了**。改为只给私有客户端方法加标注。

> ⚠️ **教训**：`@Environment(EnvType.CLIENT)` 用在方法上会让服务端**整个方法消失**，
> 不只是客户端代码段。如果一个方法同时含服务端和客户端逻辑，不能整体标注。

### 静态 mixin 审计工具

`tools/audit_mixins_263.py` —— 不启动游戏，直接对 MC 26.3 的 deobf jar 校验每一个 mixin：

- `@Mixin` 目标类是否存在
- `@Inject` / `@Redirect` / `@WrapOperation` / `@ModifyArgs` 等注入点的方法是否存在
- `@Shadow` 字段与方法是否存在
- `@Accessor` / `@Invoker` 目标是否存在

```powershell
python tools\audit_mixins_263.py    # exit 0 = 全部通过
```

它区分三类结果：`problems`（真缺陷）、`skipped`（非 MC 类/外部注入方法，仅供参考）、
以及 `NO_TARGET`（注解解析失败）。当前结果：**102 mixin / 0 problems / 8 skipped**。

---

## 一、结论速览

这次升级**不是版本号刷新**，而是 26.3 引入了两套底层 API 替换，影响面覆盖 95–119 个文件：

| 变更域 | 26.2 | 26.3 | 影响面 |
|---|---|---|---|
| 渲染后端 | `com.mojang.blaze3d.*` | `com.mojang.renderpearl.*` | 全项目 UI/渲染层 |
| 窗口 / 输入 | LWJGL **GLFW** | **SDL3** (`org.lwjgl.sdl.*`) | 41 文件 / 245 处调用 |
| 配方系统 | `SimpleJsonResourceReloadListener` 扫目录 | **数据包注册表** `RegistryLoadTask$PendingRegistration` | recipe 扩展机制 |
| 屏幕切换 | `Minecraft.setScreenAndShow()` | `Minecraft.gui.setScreen()` | 全项目 UI 跳转 |
| 映射体系 | 官方映射（Yarn 已停在 1.21.11） | 官方映射 | 不涉及 |

工作量集中在 **braid（独立窗口子系统）**，它是 GLFW 依赖的主要来源。

---

## 二、构建与依赖层改动（可直接照抄）

### gradle.properties

```diff
-minecraft_base_version=26.2
-minecraft_version=26.2
-loader_version=0.19.3
+minecraft_base_version=26.3
+minecraft_version=26.3
+loader_version=0.19.5

-fabric_version=0.152.1+26.2
+fabric_version=0.161.0+26.3

-rei_version=26.2.820
+rei_version=26.3.823        # 26.3 线可用 26.3.822 / 26.3.823 / 26.3.824

-modmenu_version=20.0.1
+modmenu_version=21.0.0

-stapi_version=3.0.1+26.1
+stapi_version=3.2.0+26.3
```

### build.gradle

```diff
-    id 'net.fabricmc.fabric-loom' version '1.15-SNAPSHOT'
+    id 'net.fabricmc.fabric-loom' version '1.16.3'    # 或 1.18-SNAPSHOT
```

> Loom 可用版本已核验：`1.16.3` / `1.17.x` / `1.18.x` / `1.19.x` 均在 Fabric Maven 上存在。

### gradle/wrapper/gradle-wrapper.properties

```diff
-distributionUrl=https\://services.gradle.org/distributions/gradle-9.2.1-bin.zip
+distributionUrl=https\://services.gradle.org/distributions/gradle-9.4.0-bin.zip
```
（PR501 用的是 9.8.0，二者均可）

### .github/workflows/build.yml

Java 版本从 `21` 提到 `25`（26.3 的 `javaVersion.majorVersion = 25`，本机 Zulu 26 也可跑），
并升级 CI action 版本（checkout v2→v7、setup-java v1→v6、upload-artifact v4→v7 等）。

---

## 三、API 迁移清单（按风险从高到低）

### 3.1 渲染层：blaze3d → RenderPearl

包路径整体平移，注意不是简单改名：

| 26.2 | 26.3 |
|---|---|
| `com.mojang.blaze3d.pipeline.RenderPipeline` | `com.mojang.renderpearl.api.pipeline.RenderPipeline` |
| `com.mojang.blaze3d.pipeline.BlendFunction` | `com.mojang.renderpearl.api.pipeline.BlendFunction` |
| `com.mojang.blaze3d.pipeline.ColorTargetState` | `com.mojang.renderpearl.api.pipeline.ColorTargetState` |
| `com.mojang.blaze3d.pipeline.BindGroupLayout` | `com.mojang.renderpearl.api.pipeline.BindGroupLayout` |
| `com.mojang.blaze3d.GpuFormat` | `com.mojang.renderpearl.api.GpuFormat` |
| `com.mojang.blaze3d.PrimitiveTopology` | `com.mojang.renderpearl.api.pipeline.PrimitiveTopology` |
| `com.mojang.blaze3d.shaders.UniformType` | `com.mojang.renderpearl.api.pipeline.UniformType` |
| `com.mojang.blaze3d.textures.GpuTextureView` | `com.mojang.renderpearl.api.textures.GpuTextureView` |
| `com.mojang.blaze3d.textures.FilterMode` | `com.mojang.renderpearl.api.textures.FilterMode` |
| `com.mojang.blaze3d.textures.AddressMode` | `com.mojang.renderpearl.api.textures.AddressMode` |
| `com.mojang.blaze3d.textures.GpuSampler` | `com.mojang.renderpearl.api.textures.GpuSampler` |
| `com.mojang.blaze3d.buffers.GpuBufferSlice` | `com.mojang.renderpearl.api.buffers.GpuBufferSlice` |
| `com.mojang.blaze3d.systems.RenderPass` | `com.mojang.renderpearl.api.commands.RenderPass` |
| `com.mojang.blaze3d.systems.CommandEncoder` | `com.mojang.renderpearl.api.commands.CommandEncoder` |
| `com.mojang.blaze3d.systems.GpuSurface` | `com.mojang.renderpearl.api.device.GpuSurface` |
| `com.mojang.blaze3d.systems.SurfaceException` | `com.mojang.renderpearl.api.device.SurfaceException` |
| `com.mojang.blaze3d.opengl.GlProgram` | `com.mojang.renderpearl.backend.opengl.GlProgram` |
| `com.mojang.blaze3d.opengl.GlTexture` | `com.mojang.renderpearl.backend.opengl.GlTexture` |
| `com.mojang.blaze3d.opengl.Uniform` | `com.mojang.renderpearl.backend.opengl.Uniform` |
| `com.mojang.blaze3d.opengl.GlStateManager` | **已删除**，需自行管理状态 |

> `GlStateManager` 被彻底移除 —— `AppState.java`、`OwoUIWidgetWrapper.java`、
> `VanillaWidgetWrapper.java` 三处需要重写状态管理逻辑，这是最容易漏的一处。

### 3.2 窗口 / 输入：GLFW → SDL3

- `org.lwjgl.glfw.*` 全部移除，改用 `org.lwjgl.sdl.*`（`SDLVideo`、`SDLKeyboard`、`SDLEvents`、`SDL_Event`）
- 键位常量改用 `com.mojang.blaze3d.platform.InputConstants.*`（PR501 明确要求走 Minecraft 内部抽象）
- 原 `mixin/braid/WindowMixin.java` 删除，改为新增 `mixin/braid/SDLEventHandlerMixin.java`
  （目标 `com.mojang.blaze3d.platform.SDLEventHandler`）
- 新增 `mixin/braid/RenderSystemAccessor.java` 暴露 `RenderSystem` 的 backend，
  供 `BraidWindow` 构造时取用（替代原先的 `MinecraftAccessor.owo$getMonitorManager()` 路径）
- `mixin/tweaks/OperatingSystemMixin.java` 整个删除 —— 26.3 改由 SDL 打开链接
- Braid 外部窗口需为 Vulkan / OpenGL 各自维护 swapchain，并用
  `GpuDevice.createSurface` + `GpuSurface.blitFromTexture`；**前端纹理不得再强转为 OpenGL 纹理**

### 3.3 配方系统：改为数据包注册表

这是 26.3 语义变更最大的一处，直接影响 owo 的 recipe 扩展：

- mixin 目标从 `SimpleJsonResourceReloadListener#scanDirectory` 改为
  `net.minecraft.resources.RegistryLoadTask$PendingRegistration#loadFromResource`
- 判定配方类型的方式从「比对 `FileToIdConverter` 实例」改为「判断 `ResourceKey.isFor(Registries.RECIPE)`」
- `RecipeManagerAccessor`（读 `RECIPE_LISTER`）删除，不再需要
- `RecipeRemainderStorage` 内部 `HashMap` 必须换成 `ConcurrentHashMap`（注册表加载线程并发）
- 原 `mixin/extension/SimpleJsonResourceReloadListenerMixin.java` 改名迁移到
  `mixin/extension/recipe/PendingRegistrationMixin.java`

> 附带影响：配方现在是数据包注册表后，未注册的配方类型会导致**加载期致命错误**（26.2 只是静默失败）。
> 仓库里 `src/testmod/resources/data/uwu/recipe/uwu_shaped_recipe.json5` 引用了一个已被注释掉的
> 配方类型，必须删除（PR501 已删）。

### 3.4 屏幕切换 API

26.3 的 `Minecraft.setScreenAndShow()` 会强制多渲染一帧不绘制世界的画面。
**所有普通界面切换都改用 `Minecraft.getInstance().gui.setScreen(...)`**。
涉及文件：`OwoDebugCommands`、`OwoConfigCommand`、`ConfigScreen`、`RestartRequiredScreen`、
`ItemGroupButton`、`UwuClient` 等。

### 3.5 其他被删除 / 移动的 MC API

| 26.2 | 26.3 状态 |
|---|---|
| `net.minecraft.server.packs.resources.SimpleJsonResourceReloadListener` | 已删除 |
| `net.minecraft.world.item.crafting.RecipeManager`（作为 mixin 目标） | 改为注册表任务 |
| `net.minecraft.util.Util`（部分用途） | 被移除/替换 |
| `net.minecraft.client.renderer.texture.TextureManager` | 移动（`SpriteWidget` 需改） |
| `net.minecraft.client.resources.model.sprite.Material` | 移动 |
| `net.minecraft.resources.Identifier` | 仍有，但语义调整 |
| `net.minecraft.client.DeltaTracker` | 移动 |
| `net.minecraft.world.level.storage.loot.predicates.LootItemCondition` | 改用新的可选条件持有者 |
| `net.minecraft.world.level.storage.loot.providers.number.ConstantValue` / `UniformGenerator` | 改用新的数量提供器 |
| `net.minecraft.world.level.chunk.BulkSectionAccess` | 移除 → `Copenhagen` mixin 改用 `@WrapOperation` |
| `net.minecraft.world.level.levelgen.feature.configurations.OreConfiguration` | 移除 → 同上 |
| `net.minecraft.core.component.DataComponentPatch` | `SetComponentsFunctionAccessor` 整体删除 |
| `net.minecraft.world.item.crafting` 的 `ItemStack` 用法 | 改为 `ItemStackTemplate` |
| `com.mojang.serialization.MapCodec` | testmod 用法调整 |

---

## 四、Mixin / AccessWidener 配置改动

### owo.mixins.json

**需删除的条目：**
- `SetComponentsFunctionAccessor`（目标类已删）
- `extension.SimpleJsonResourceReloadListenerMixin`（改名为 PendingRegistrationMixin）
- `extension.recipe.RecipeManagerAccessor`（改名为 PendingRegistrationMixin）
- `ui.CommandEncoderAccessor`（CommandEncoder 迁到 renderpearl）
- `braid.WindowMixin`（SDL 化后删除）
- `shader.GlProgramAccessor`（PR501 路线下删除；PR500 路线下保留并改指向）
- `tweaks.OperatingSystemMixin`（SDL 接管链接打开）

**需新增的条目：**
- `extension.recipe.PendingRegistrationMixin`
- `braid.SDLEventHandlerMixin`
- `braid.RenderSystemAccessor`
- `ui.access.PictureInPictureRendererAccessor`（PR500 路线）

### owo.accesswidener

PR500 路线追加两条（PR501 路线未加）：

```
accessible field net/minecraft/client/gui/render/pip/PictureInPictureRenderer textureView Lcom/mojang/renderpearl/api/textures/GpuTextureView;
accessible field net/minecraft/client/gui/render/pip/PictureInPictureRenderer depthTextureView Lcom/mojang/renderpearl/api/textures/GpuTextureView;
```

### 自定义 shader（`src/main/resources/assets/owo/shaders/core/`）

GLSL 版本与包含方式需更新：

```diff
-#version 150
+#version 330
+#extension GL_ARB_separate_shader_objects : require

-#moj_import <minecraft:dynamictransforms.glsl>
+#include <minecraft:dynamictransforms.glsl>

-out vec4 fragColor;
+layout(location = 0) out vec4 fragColor;
```

三个文件都要改：`blur.fsh`、`blur.vsh`、`spectrum.fsh`。

另外 owo 自己维护的 uniform 映射表在 26.3 不再存在于 `GlProgram` 内，
需新增 `mixin/shader/GlProgramMixin.java`（`priority = 1100`）在 `setupBindGroupLayouts`
处重建 `Map<String, Uniform>`，并让 `GlProgramAccessor` 改读该字段
（`@Accessor("owo$uniformsByName")`）。

---

## 五、两条可选路线

上游有两份独立的 26.3 移植尝试，均未合并：

| | PR #501 | PR #500 |
|---|---|---|
| 标题 | Port to 26.3 | Port owo library and Braid windows to 26.3 SDL and RenderPearl APIs |
| 状态 | closed（未合并） | open，draft |
| 规模 | 41 commits，119 文件，+1087/-1037 | 2 commits，95 文件，+801/-682 |
| 特色 | 移植更彻底，含 recipe 注册表改造、SDL 全量重写 | 附带 `PORTING_26_3.md` 构建文档 + JUnit 回归测试 |
| 测试 | Linux/Wayland + Nvidia，Vulkan 与 OpenGL 均通过 | Java 25 全量构建通过，675 个 accessor/invoker 静态审计通过 |
| 短板 | — | 运行时 mixin 审计未做，Vulkan 运行时行为未验证 |

**两份 diff 都可以直接应用到本目录**（已用 `git apply --check` 验证）：

```bash
git apply --check pr500.diff                                   # exit 0
git apply --check --exclude='gradle/wrapper/gradle-wrapper.jar' pr501.diff   # exit 0
```

> PR501 唯一冲突是 `gradle-wrapper.jar` 的二进制补丁 —— Git diff 的固有限制，
> 手动执行 `gradle wrapper --gradle-version 9.4.0` 即可。

参考实现位置：`https://github.com/wisp-forest/owo-lib/pull/501`、`/pull/500`

---

## 六、建议执行顺序

1. **打 tag 备份当前 26.2 状态**（或直接用 git 分支）
2. 升 `gradle.properties` 五个版本号 + `build.gradle` 的 Loom 版本 + wrapper 版本
3. 先跑一次 `./gradlew compileJava`，用编译错误清单驱动迁移（比逐文件改更高效）
4. 按「blaze3d → RenderPearl」批量改 import（占编译错误大头）
5. 单独攻 braid 子系统（GLFW → SDL3），这是唯一需要真正重写逻辑的部分
6. 改 recipe 注册表 hook（`PendingRegistrationMixin` + `ConcurrentHashMap`）
7. 改 `owo.mixins.json` / `owo.accesswidener` / 三个 shader 文件
8. 全局替换 `setScreenAndShow` → `gui.setScreen`
9. `git apply` PR500 或 PR501 的 diff 补齐遗漏（两份都不完全覆盖，都带自己的盲区）
10. `./gradlew build` 全量构建 + 独立游戏目录实机验证（Vulkan 与 OpenGL 都要试）

---

## 七、已知风险

- **PR500 自述**：最终「注册 accessor 兼容性调整」仍需一次全新隔离运行时审计才能发版
- **PR501 自述**：Vulkan 路径只验证到编译层面，硬件 GPU 与 shader pack 行为未验证
- 两者共同点：**编译通过 ≠ mixin 变换通过 ≠ 渲染正确**。必须实机跑
- `GlStateManager` 移除后状态管理逻辑要自己兜住，容易出现难以定位的渲染错乱
- 配方改数据包注册表后，自定义配方类型的注册时机要重新对齐
