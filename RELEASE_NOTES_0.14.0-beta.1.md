## owo-lib 0.14.0-beta.1 for Minecraft 26.3

Minecraft 26.3 兼容版本，基于上游 PR #501 的移植。

### 主要变更

26.3 替换了两套底层 API，这次移植主要围绕它们展开：

| 变更域 | 26.2 | 26.3 |
|---|---|---|
| 渲染层 | `com.mojang.blaze3d.*` | `com.mojang.renderpearl.*` |
| 窗口 / 输入 | LWJGL **GLFW** | **SDL3** (`org.lwjgl.sdl.*`) |
| 配方系统 | `SimpleJsonResourceReloadListener` 扫目录 | **数据包注册表** `RegistryLoadTask$PendingRegistration` |
| 屏幕切换 | `Minecraft.setScreenAndShow()` | `Minecraft.gui.setScreen()` |

其余同步更新：键位常量改走 `com.mojang.blaze3d.platform.InputConstants`，自定义 shader 从 GLSL `#version 150` 升到 `330` + `GL_ARB_separate_shader_objects`，`#moj_import` 改为 `#include`。

### API 破坏性变更

移除了 8 个 public 类型：`SetComponentsFunctionAccessor`、`WindowMixin`、`SimpleJsonResourceReloadListenerMixin`、`RecipeManagerAccessor`、`GlProgramAccessor`、`OperatingSystemMixin`、`CommandEncoderAccessor`、`GlRenderPassMixin`。

新增 5 个：`RenderSystemAccessor`、`SDLEventHandlerMixin`、`PendingRegistrationMixin`、`PictureInPictureRendererAccessor`、`FrontendGpuDeviceMixin`。

新增顶层类 `io.wispforest.owo.braid.core.BraidScreenSettings`（原为 `BraidScreen.Settings` 嵌套类，嵌套在客户端类里会导致服务端类加载失败）。`BraidScreen.Settings` 保留为 `@Deprecated` 兼容别名。

### 依赖

Minecraft 26.3 · Fabric Loader ≥ 0.19.5 · Fabric API ≥ 0.164.0+26.3

> 注意：26.3 没有 Yarn 映射，Fabric 的 intermediary 停在 1.21.11，本版本使用 Mojang 官方映射，无需 remap。

### 验证状态

已通过：clean build、`validateAccessWidener`、testmod 编译、无 GUI 服务端启动、102 个 mixin 对 26.3 jar 的静态审计（`tools/audit_mixins_263.py`，0 问题）。

**尚未实机验证**：客户端渲染路径（braid 独立窗口的创建/缩放/关闭、SDL 输入、shader 效果）未做图形界面下的运行验证。首次使用请重点检查这些方面。

### 安装

把 `owo-lib-0.14.0-beta.1+26.3.jar` 放进 MC 26.3 的 `mods/` 目录。

---

这是 Beta 版本，API 可能继续调整。上游仓库：[wisp-forest/owo-lib](https://github.com/wisp-forest/owo-lib)
