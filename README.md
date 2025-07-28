# VMware-Destroyer

https://img.shields.io/badge/License-MIT-blue.svg
https://img.shields.io/badge/Python-3.6%2B-green.svg
https://img.shields.io/badge/Platform-Windows-lightgrey.svg

**VMware-Destroyer** 是一个专业的工具，用于彻底卸载 VMware 产品及其所有残留文件、注册表项和服务。它解决了官方卸载程序无法完全清理系统的问题，确保您可以重新安装 VMware 而不会遇到任何冲突。

## 功能特点

✅ **彻底清理** - 删除所有 VMware 相关文件、目录、注册表项和服务
✅ ​**​管理员权限验证​**​ - 确保以管理员身份运行
✅ ​**​可视化进度​**​ - 带有时尚进度条的现代化界面
✅ ​**​详细日志​**​ - 记录所有操作步骤和结果
✅ ​**​安全模式​**​ - 提供测试模式，可在虚拟环境中安全测试
✅ ​**​多版本支持​**​ - 支持 VMware Workstation, Player, Fusion, ESXi 等
✅ ​**​自动重启提示​**​ - 卸载完成后提示重启系统

## 为什么需要 VMware-Destroyer？

当您尝试卸载 VMware 产品时，可能会遇到以下问题：

- 卸载后无法重新安装相同产品
- 安装过程中出现错误 28030、28053 或 1706
- 系统残留文件阻止新版本安装
- 注册表项未被完全清除

VMware-Destroyer 解决了这些问题，确保您的系统完全干净，可以重新安装 VMware 产品。

## 安装与使用

### 前提条件

- Windows 7/8/10/11 系统
- Python 3.6 或更高版本
- 管理员权限

### 安装步骤

1. **克隆仓库**：

   ```
   git clone https://github.com/yourusername/VMware-Destroyer.git
   cd VMware-Destroyer
   ```

2. **安装依赖**：

   ```
   pip install -r requirements.txt
   ```

### 使用方法

1. **以管理员身份运行**：
   - 右键点击 `vmware_destroyer.py`
   - 选择"以管理员身份运行"
2. **图形界面操作**：
   - 阅读警告信息
   - 点击"开始卸载"按钮
   - 观察进度条和日志区域
   - 完成后重启系统

## 技术细节

### 清理内容

- **文件系统**：
  - 程序文件目录 (`Program Files\VMware`)
  - 应用数据目录 (`AppData\Local\VMware`, `AppData\Roaming\VMware`)
  - 系统文件 (`Windows\System32\drivers\vm*.sys`)
  - 桌面快捷方式
- **注册表**：
  - `HKEY_LOCAL_MACHINE\SOFTWARE\VMware, Inc.`
  - `HKEY_CLASSES_ROOT\Installer\Products\*VMware*`
  - `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{VMware GUID}`
- **服务**：
  - VMware Authorization Service
  - VMware DHCP Service
  - VMware NAT Service
  - VMware USB Arbitration Service

### 安全特性

- 管理员权限验证
- 操作前警告提示
- 错误处理和日志记录
- 测试模式（虚拟环境）
- 操作完成后需要重启系统

## 测试模式

VMware-Destroyer 提供安全的测试模式：

```
python vmware_destroyer.py --test
```

在测试模式下：

- 所有操作在虚拟环境中进行
- 不修改真实文件系统或注册表
- 使用临时目录模拟卸载过程
- 完成后自动清理测试环境

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 仓库
2. 创建新分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -am 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 [MIT 许可证](https://yuanbao.tencent.com/chat/naQivTmsDa/LICENSE)。

## 免责声明

此软件按"原样"提供，不提供任何明示或暗示的担保。使用此软件的风险由用户自行承担。作者对因使用此软件而产生的任何损失或损害不承担责任。

**注意**：使用前请备份重要数据，特别是虚拟机文件。

------

**VMware-Destroyer** - 彻底清理您的系统，为新的 VMware 安装做好准备！