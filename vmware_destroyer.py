import os
import sys
import ctypes
import shutil
import subprocess
import winreg
import win32serviceutil
import win32service
import win32event
import servicemanager
import time
import threading
import psutil
from tkinter import *
from tkinter import ttk, messagebox, font, PhotoImage
from PIL import Image, ImageTk

# ====================== 工具函数 ======================
def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def restart_as_admin():
    """以管理员权限重新启动程序"""
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit(0)

def delete_path(path):
    """删除文件或目录"""
    if os.path.exists(path):
        try:
            if os.path.isfile(path):
                os.remove(path)
                return True, ""
            elif os.path.isdir(path):
                # 如果目录非空，先尝试删除内容
                for root, dirs, files in os.walk(path, topdown=False):
                    for name in files:
                        try:
                            os.remove(os.path.join(root, name))
                        except:
                            pass
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except:
                            pass
                # 最后删除目录本身
                shutil.rmtree(path, ignore_errors=True)
                return True, ""
        except Exception as e:
            return False, str(e)
    return False, "路径不存在"

def recursive_delete_key(root, sub_key):
    """递归删除注册表项"""
    try:
        full_key = f"{root}\\{sub_key}"
        with winreg.OpenKey(getattr(winreg, root), sub_key, 0, winreg.KEY_ALL_ACCESS) as key:
            index = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(key, index)
                    recursive_delete_key(root, f"{sub_key}\\{sub_name}")
                    index += 1
                except OSError:
                    break
        winreg.DeleteKey(getattr(winreg, root), sub_key)
        return True, ""
    except Exception as e:
        return False, str(e)

def delete_registry_key(root_key, subkey):
    """删除注册表项"""
    try:
        winreg.DeleteKey(root_key, subkey)
        return True, ""
    except PermissionError:
        # 如果是权限问题，尝试获取所有权
        try:
            # 尝试递归删除
            return recursive_delete_key(root_key, subkey)
        except Exception as e:
            return False, str(e)
    except FileNotFoundError:
        return False, "键不存在"
    except Exception as e:
        return False, str(e)

def delete_registry_value(root_key, subkey, value_name):
    """删除注册表值"""
    try:
        with winreg.OpenKey(root_key, subkey, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, value_name)
        return True, ""
    except FileNotFoundError:
        return False, "值不存在"
    except Exception as e:
        return False, str(e)

def kill_processes(process_names):
    """结束指定名称的进程"""
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'].lower() in [name.lower() for name in process_names]:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    time.sleep(1)  # 等待进程结束

def stop_services():
    """停止VMware相关服务"""
    services = [
        "VMAuthdService", "VMnetDHCP", "VMware NAT Service", 
        "VMUSBArbService", "VMwareHostd", "VMwareWorkstationServer", 
        "VMware WSX Service", "VGAuthService"
    ]
    
    kill_processes(["vmware.exe", "vmplayer.exe", "vmtoolsd.exe"])
    
    for service in services:
        try:
            status = win32serviceutil.QueryServiceStatus(service)
            if status[1] == win32service.SERVICE_RUNNING:
                win32serviceutil.StopService(service)
            win32serviceutil.ChangeServiceConfig(
                service,
                None,
                None,
                startType=win32service.SERVICE_DISABLED
            )
        except Exception:
            continue

def get_visual_style():
    """获取系统视觉样式"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            apps_use_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if apps_use_light else "dark"
    except:
        return "light"

# ====================== 卸载功能 ======================
class VMwareUninstaller:
    def __init__(self, progress_callback, log_callback, status_callback):
        self.progress = 0
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.total_steps = 100
        
    def update_progress(self, increment, message=None):
        """更新进度和状态"""
        if message:
            self.log_callback(message)
        self.progress = min(self.progress + increment, 100)
        self.progress_callback(self.progress)
        time.sleep(0.05)  # 短暂暂停，让UI更新
        
    def start_uninstall(self):
        """开始卸载过程"""
        self.log_callback("=== 开始VMware彻底卸载 ===")
        
        # 阶段1: 停止服务和进程 (10%)
        self.status_callback("停止VMware服务和进程...")
        self.update_progress(0, "> 尝试结束所有VMware相关进程")
        kill_processes(["vmware", "vmplayer", "vmtoolsd"])
        
        self.update_progress(5, "> 停止VMware服务并禁用启动")
        stop_services()
        
        # 阶段2: 删除文件和目录 (45%)
        self.status_callback("删除文件和目录...")
        paths = self.get_paths_to_delete()
        
        self.update_progress(2, "> 准备删除VMware安装文件和目录")
        deleted_count = 0
        total_paths = len(paths)
        
        for path in paths:
            success, error = delete_path(path)
            if success:
                self.update_progress(40/total_paths, f"✓ 已删除: {path}")
                deleted_count += 1
            else:
                self.update_progress(40/total_paths, f"⚠️ 删除失败({error}): {path}")
        
        # 阶段3: 删除注册表项 (35%)
        self.status_callback("清理注册表项...")
        self.update_progress(2, "> 准备删除VMware注册表项")
        
        keys = self.get_registry_keys()
        deleted_keys = 0
        total_keys = len(keys)
        
        for root_key, subkey in keys:
            success, error = delete_registry_key(root_key, subkey)
            if success:
                self.update_progress(33/total_keys, f"✓ 已删除注册表项: {winreg.EnumKey(root_key, None)[0]} > {subkey}")
                deleted_keys += 1
            else:
                self.update_progress(33/total_keys, f"⚠️ 注册表删除失败({error}): {subkey}")
        
        # 阶段4: 清理其他组件 (5%)
        self.status_callback("清理剩余组件...")
        self.update_progress(1, "> 尝试删除__vmware_user__")
        subprocess.run('net user __vmware_user__ /delete', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.update_progress(1, "> 尝试删除__vmware__组")
        subprocess.run('net localgroup __vmware__ /delete', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.update_progress(3, "> 清理完成!")
        
        # 阶段5: 完成 (5%)
        self.status_callback("卸载完成!")
        self.log_callback("=== VMware卸载成功完成 ===")
        self.log_callback("*** 请重启计算机以使更改生效 ***")
    
    def get_paths_to_delete(self):
        """获取所有需要删除的路径"""
        program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
        program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
        appdata = os.environ.get('APPDATA', '')
        local_appdata = os.environ.get('LOCALAPPDATA', '')
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        public_desktop = os.path.join(os.environ['PUBLIC'], 'Desktop')
        
        paths = [
            # 程序目录
            os.path.join(program_files, 'VMware'),
            os.path.join(program_files_x86, 'VMware'),
            
            # 应用数据目录
            os.path.join(program_data, 'VMware'),
            os.path.join(appdata, 'VMware'),
            os.path.join(local_appdata, 'VMware'),
            
            # 开始菜单
            os.path.join(program_data, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'VMware'),
            
            # 桌面快捷方式
            *[os.path.join(desktop, f) for f in os.listdir(desktop) if 'VMware' in f and f.endswith('.lnk')],
            *[os.path.join(public_desktop, f) for f in os.listdir(public_desktop) if 'VMware' in f and f.endswith('.lnk')],
            
            # 系统文件
            r"C:\Windows\system32\vmnat.exe",
            r"C:\Windows\system32\vmnetbridge.exe",
            r"C:\Windows\system32\VMNetDHCP.exe",
            r"C:\Windows\system32\vmnetdhcp.leases",
            r"C:\Windows\system32\vmxw2ksetup.dll",
            r"C:\Windows\system32\vnetprobe.exe",
            r"C:\Windows\system32\vnetprobelib.dll",
            r"C:\Windows\system32\vnetinst.dll",
            r"C:\Windows\system32\vnetlib.dll",
            r"C:\Windows\system32\vnetlib.exe",
            r"C:\Windows\system32\drivers\vmnet.sys",
            r"C:\Windows\system32\drivers\vmnetx.sys",
            r"C:\Windows\system32\drivers\VMparport.sys",
            r"C:\Windows\system32\drivers\vmx86.sys",
            r"C:\Windows\system32\drivers\vmnetadapter.sys",
            r"C:\Windows\system32\drivers\vmnetbridge.sys",
            r"C:\Windows\system32\drivers\vmnetuserif.sys",
            r"C:\Windows\system32\drivers\hcmon.sys",
            r"C:\Windows\system32\drivers\vmusb.sys",
            r"C:\Windows\system32\drivers\VBoxNetLwf.sys",
            r"C:\Windows\system32\drivers\VBoxNetAdp.sys",
            r"C:\Windows\system32\drivers\VBoxNetNAT.sys",
        ]
        
        # 添加Windows安装文件中可能的其他文件
        additional_files = [
            "vmnat", "vmnetbridge", "vmnetdhcp", "vnetprobe", "vmxw2ksetup", 
            "vnetprobelib", "vnetinst", "vnetlib", "vmnet", "vmnetx", "vmparport",
            "vmx86", "vmnetadapter", "vmnetbridge", "vmnetuserif", "hcmon", "vmusb"
        ]
        
        for file in additional_files:
            paths.extend([
                os.path.join(r"C:\Windows\System32", file + ".exe"),
                os.path.join(r"C:\Windows\System32", file + ".dll"),
                os.path.join(r"C:\Windows\SysWOW64", file + ".exe"),
                os.path.join(r"C:\Windows\SysWOW64", file + ".dll")
            ])
        
        return paths
    
    def get_registry_keys(self):
        """获取所有需要删除的注册表项"""
        keys = [
            # VMware 主键
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VMware, Inc."),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\VMware, Inc."),
            
            # Workstation 各种版本
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A3FF5CB2-FB35-4658-8751-9EDE1D65B3AA}"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{0D94F75A-0EA6-4951-B3AF-B145FA9E05C6}"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{98D1A713-438C-4A23-8AB6-41B37C4A2D47}"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A53A11EA-0095-493F-86FA-A15E8A86A405}"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{F229E5CB-8525-47EE-AB9C-3BAAD1E6B0B1}"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{C90560C2-4750-4E77-BFAE-7C3E38DCFFD3}"),
            
            # 通用安装程序键
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\Features\317A1D89C83432A4A86B143BC7A4D274"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\Products\317A1D89C83432A4A86B143BC7A4D274"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\Features\2BC5FF3A53BF85647815E9EDD1563BAA"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\Products\2BC5FF3A53BF85647815E9EDD1563BAA"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\Features\AE11A35A5900F39468AF1AE5A8684A50"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\Products\AE11A35A5900F39468AF1AE5A8684A50"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\Products\7A26F0EA2A1AF704F9C48439B99DDAD8"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\Products\7A79579133DA8984D9E8376086814B46"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Installer\UpgradeCodes\3F935F414A4C79542AD9C8D157A3CC39"),
            
            # 其他相关键
            (winreg.HKEY_CLASSES_ROOT, r"Installer\Products\7A26F0EA2A1AF704F9C48439B99DDAD8"),
            (winreg.HKEY_CLASSES_ROOT, r"Installer\Products\7A79579133DA8984D9E8376086814B46"),
            (winreg.HKEY_CLASSES_ROOT, r"Installer\UpgradeCodes\3F935F414A4C79542AD9C8D157A3CC39"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\Applications\vmware.exe"),
        ]
        
        return keys

# ====================== GUI界面 ======================
class UninstallerGUI:
    def __init__(self):
        self.root = Tk()
        
        # 高DPI适配
        self.setup_high_dpi()
        
        self.root.title("VMware 完全卸载工具")
        self.root.geometry("800x1250")  # 增大初始窗口大小
        self.root.resizable(True, True)
        self.root.minsize(950, 700)  # 增大最小窗口大小
        
        self.style = self.create_styles()
        
        # 设置窗口图标
        try:
            self.root.iconbitmap(default=self.get_icon_path())
        except:
            pass
        
        # 创建UI控件
        self.create_widgets()
        
    def setup_high_dpi(self):
        """设置高DPI适配"""
        try:
            # Windows高DPI感知设置
            import ctypes
            from ctypes import wintypes
            
            # 设置DPI感知
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
            except:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except:
                    pass
            
            # 获取DPI缩放比例
            try:
                hdc = ctypes.windll.user32.GetDC(0)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                ctypes.windll.user32.ReleaseDC(0, hdc)
                self.dpi_scale = dpi / 96.0
            except:
                self.dpi_scale = 1.0
            
            # 设置Tkinter的缩放
            if self.dpi_scale > 1.0:
                self.root.tk.call('tk', 'scaling', self.dpi_scale)
                
        except Exception as e:
            self.dpi_scale = 1.0
            print(f"DPI设置失败: {e}")
            
    def get_scaled_size(self, size):
        """根据DPI缩放获取调整后的尺寸"""
        return int(size * self.dpi_scale)
        
    def get_icon_path(self):
        """获取图标路径"""
        temp_path = os.path.join(os.environ['TEMP'], 'vmware_uninstaller.ico')
        if not os.path.exists(temp_path):
            # 创建临时图标文件
            icon_data = b"AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAABILAAASCwAAAAAAAAAAAAAAMDAw/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP//////////////////////////wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD//////////////////////////8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA//////////////////////////9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3//////////////////////21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf//////////////////////bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t//////////////////////9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3//////////////////////////21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf//////////////////////bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t//////////////////////9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3//////////////////////////21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf9tbW3/bW1t/21tbf//////////////////////////wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD//////////////////////////8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA/8DAwP/AwMD/wMDA//8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            with open(temp_path, 'wb') as f:
                f.write(icon_data)
        return temp_path
    
    def create_styles(self):
        """创建UI样式"""
        style = ttk.Style(self.root)
        
        # 设置主题
        theme = get_visual_style()
        if theme == "dark":
            style.theme_use('alt')
            bg_color = "#2d2d30"
            fg_color = "#ffffff"
            accent_color = "#007acc"
            warning_color = "#ff5555"
        else:
            style.theme_use('clam')
            bg_color = "#f0f0f0"
            fg_color = "#000000"
            accent_color = "#1e88e5"
            warning_color = "#e53935"
        
        # 根据DPI调整字体大小
        base_font_size = max(9, int(10 * self.dpi_scale))
        title_font_size = max(14, int(16 * self.dpi_scale))
        button_font_size = max(10, int(12 * self.dpi_scale))
        
        # 配置样式
        self.root.configure(bg=bg_color)
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, 
                       font=('Arial', base_font_size))
        style.configure('TButton', font=('Arial', base_font_size), 
                       padding=self.get_scaled_size(6))
        
        # 配置突出的主按钮样式
        style.configure('Accent.TButton', 
                       font=('Arial', button_font_size, 'bold'),
                       padding=(self.get_scaled_size(25), self.get_scaled_size(18)),
                       background=accent_color,
                       foreground='white',
                       borderwidth=2,
                       relief='raised')
        
        # 鼠标悬停效果
        style.map('Accent.TButton',
                 background=[('active', '#ff4444' if theme == "dark" else '#c62828')],
                 foreground=[('active', 'white')])
        
        style.configure('Title.TLabel', font=('Arial', title_font_size, 'bold'), 
                       foreground=accent_color, background=bg_color)
        style.configure('Warning.TLabel', foreground=warning_color, background=bg_color)
        style.configure('Info.TLabel', foreground='#888888', background=bg_color)
        style.configure('Log.TFrame', background='#1e1e1e' if theme == "dark" else '#ffffff')
        
        style.configure("TProgressbar", thickness=self.get_scaled_size(20), 
                       background=accent_color, 
                       troughcolor='#cccccc' if theme == "light" else '#444444')
        
        return style
    
    def create_widgets(self):
        """创建UI控件"""
        # 计算调整后的边距和间距
        padding_x = self.get_scaled_size(25)
        padding_y = self.get_scaled_size(20)
        small_padding = self.get_scaled_size(10)
        
        # 标题栏
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=X, padx=padding_x, pady=(padding_y, small_padding))
        
        title_label = ttk.Label(title_frame, text="VMware 完全卸载工具", style='Title.TLabel')
        title_label.pack(side=LEFT)
        
        # 添加版本和状态信息
        info_label = ttk.Label(title_frame, text="v2.0 - 一键彻底清理", 
                              font=('Arial', max(9, int(10 * self.dpi_scale))), style='Info.TLabel')
        info_label.pack(side=RIGHT)
        
        # 警告信息
        warning_frame = ttk.Frame(self.root, relief='groove', borderwidth=2)
        warning_frame.pack(fill=X, padx=padding_x, pady=small_padding)
        
        ttk.Label(warning_frame, text="⚠️ 重要警告", 
                 font=('Arial', max(11, int(12 * self.dpi_scale)), 'bold'), 
                 style='Warning.TLabel').pack(pady=(small_padding//2, 0))
        
        ttk.Label(warning_frame, text="此工具将彻底删除所有VMware组件，包括:", 
                 font=('Arial', max(8, int(9 * self.dpi_scale)))).pack(anchor='w', 
                 padx=small_padding, pady=(small_padding,0))
        
        bullet_font = ('Arial', max(8, int(9 * self.dpi_scale)))
        ttk.Label(warning_frame, text="• VMware安装文件和目录", 
                 font=bullet_font).pack(anchor='w', padx=padding_x)
        ttk.Label(warning_frame, text="• VMware系统服务和驱动程序", 
                 font=bullet_font).pack(anchor='w', padx=padding_x)
        ttk.Label(warning_frame, text="• VMware注册表项", 
                 font=bullet_font).pack(anchor='w', padx=padding_x)
        
        ttk.Label(warning_frame, text="完成后必须重启系统才能使更改生效", 
                 font=('Arial', max(8, int(9 * self.dpi_scale)), 'bold'), 
                 style='Warning.TLabel').pack(anchor='w', padx=small_padding, 
                 pady=(small_padding, small_padding//2))
        
        # 进度区域
        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill=X, padx=padding_x, pady=padding_y)
        
        self.status_var = StringVar(value="准备卸载...")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var, 
                                font=('Arial', max(9, int(10 * self.dpi_scale)), 'bold'))
        status_label.pack(anchor='w', padx=small_padding//2)
        
        self.progress_var = DoubleVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                      length=self.get_scaled_size(900), mode='determinate')
        progress_bar.pack(fill=X, padx=small_padding//2, pady=small_padding//2)
        
        # 日志区域
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill=BOTH, expand=True, padx=padding_x, pady=(0, padding_y))
        
        log_container = ttk.Frame(log_frame, style='Log.TFrame')
        log_container.pack(fill=BOTH, expand=True)
        
        # 创建滚动条
        scrollbar = Scrollbar(log_container)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 创建日志文本框
        log_font_size = max(8, int(9 * self.dpi_scale))
        self.log_text = Text(log_container, wrap=WORD, yscrollcommand=scrollbar.set,
                            bg='#1e1e1e' if get_visual_style() == "dark" else '#ffffff',
                            fg='#d4d4d4' if get_visual_style() == "dark" else '#000000',
                            borderwidth=1, relief="solid", 
                            font=("Consolas", log_font_size))
        self.log_text.pack(fill=BOTH, expand=True, padx=2, pady=2)
        self.log_text.configure(state='disabled')
        
        scrollbar.config(command=self.log_text.yview)
        
        # 按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=X, padx=padding_x, pady=(small_padding, padding_y))
        
        # 创建一个特殊的框架来突出显示主按钮
        main_button_frame = ttk.Frame(button_frame)
        main_button_frame.pack(fill=X, pady=(small_padding, 0))
        
        # 主要的开始卸载按钮 - 使其更突出
        self.start_button = ttk.Button(main_button_frame, text="🗑️ 开始完全卸载 VMware", 
                                      command=self.start_uninstall,
                                      style="Accent.TButton")
        self.start_button.pack(pady=small_padding)
        
        # 次要按钮区域
        secondary_button_frame = ttk.Frame(button_frame)
        secondary_button_frame.pack(fill=X, pady=(small_padding//2, 0))
        
        ttk.Button(secondary_button_frame, text="重启计算机", command=self.restart_computer,
                  style="TButton").pack(side=RIGHT, padx=(0, small_padding))
        
        ttk.Button(secondary_button_frame, text="退出", command=self.root.destroy,
                  style="TButton").pack(side=RIGHT)
        
        # 状态栏
        statusbar_frame = ttk.Frame(self.root)
        statusbar_frame.pack(fill=X, padx=0, pady=(0, small_padding//2))
        
        self.statusbar_var = StringVar(value="就绪")
        statusbar = ttk.Label(statusbar_frame, textvariable=self.statusbar_var,
                             font=('Arial', max(7, int(8 * self.dpi_scale))), 
                             style='Info.TLabel')
        statusbar.pack(side=LEFT, padx=padding_x)
        
        version_label = ttk.Label(statusbar_frame, text="v2.0 © 2024", 
                                 font=('Arial', max(7, int(8 * self.dpi_scale))), 
                                 style='Info.TLabel')
        version_label.pack(side=RIGHT, padx=padding_x)
    
    def log_message(self, message):
        """添加日志消息"""
        self.log_text.configure(state='normal')
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)
        self.log_text.configure(state='disabled')
        self.statusbar_var.set(f"记录: {message[:50]}{'...' if len(message) > 50 else ''}")
    
    def update_status(self, status):
        """更新状态文本"""
        self.status_var.set(status)
        self.root.update()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_var.set(value)
        self.root.update()
    
    def start_uninstall(self):
        """开始卸载过程"""
        if not is_admin():
            self.log_message("需要管理员权限，正在重新启动...")
            self.root.after(2000, restart_as_admin)
            return
            
        # 禁用开始按钮
        self.start_button.configure(state='disabled', text="🔄 正在卸载中...")
        
        # 创建卸载程序
        uninstaller = VMwareUninstaller(
            self.update_progress,
            self.log_message,
            self.update_status
        )
        
        # 在单独的线程中运行卸载过程
        thread = threading.Thread(target=uninstaller.start_uninstall, daemon=True)
        thread.start()
    
    def restart_computer(self):
        """重启计算机"""
        if messagebox.askyesno("重启计算机", "确定要立即重启计算机吗？"):
            subprocess.run(["shutdown", "/r", "/t", "10"])
            self.log_message("计算机将在10秒后重启...")

# ====================== 主程序 ======================
if __name__ == "__main__":
    if not is_admin():
        restart_as_admin()
    
    app = UninstallerGUI()
    app.root.mainloop()