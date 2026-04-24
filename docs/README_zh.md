# Pico I2C Bridge

[![GitHub release](https://img.shields.io/github/v/release/Hi-Barry/Pico-I2C-Bridge)](https://github.com/Hi-Barry/Pico-I2C-Bridge/releases)
[![License](https://img.shields.io/github/license/Hi-Barry/Pico-I2C-Bridge)](../LICENSE)

基于 CircuitPython 的 Raspberry Pi Pico RP2040 固件，实现 USB CDC 转 I2C 桥接功能。适用于微雪 XIAO RP2040 / RP2040-Zero 开发板。

## 硬件信息

- **开发板:** Seeed Studio XIAO RP2040 / RP2040-Zero
- **I2C 引脚:** 
  - SDA: GP2
  - SCL: GP3
- **状态灯:** GP16 NeoPixel
- **USB:** 原生 USB CDC（虚拟串口）

## 功能特性

- 🔌 **USB CDC 接口** - 虚拟串口，无需额外驱动
- 🔁 **I2C 总线恢复** - 自动检测并恢复 I2C 总线死锁
- 🐕 **硬件看门狗** - 5 秒超时防止系统死机
- 📦 **内存预分配** - 固定大小缓冲区避免 GC 延迟
- 🚨 **结构化错误码** - `ERR:NACK`、`ERR:BUSY`、`ERR:NOBUS`、`ERR:UNK`
- 🔍 **协议版本查询** - 通过虚拟地址 `0x00` 查询固件版本
- 💡 **NeoPixel 状态指示** - 可视化连接和数据活动状态

## 通信协议

### 命令格式

| 字节 | 字段 | 说明 |
|------|------|------|
| 0 | 地址（8 位） | I2C 设备地址 + 读写位（最低位：0=写，1=读） |
| 1 | 寄存器 | 寄存器地址或命令字节 |
| 2+ | 数据 | 写入数据或读取长度（读操作） |

### 读操作

```
发送：[0xA1, 0x05, 0x10]  # 从设备 0x50 读取 16 字节，寄存器地址 0x05
接收：[数据...(16 字节)]\r\n
```

### 写操作

```
发送：[0xA0, 0x05, 0x12, 0x34]  # 向设备 0x50 写入 0x1234，寄存器地址 0x05
接收：\r\n (成功) 或 ERR:NACK\r\n
```

### 版本查询

```
发送：[0x00, 0xFF]  # 虚拟地址 0x00，寄存器 0xFF
接收：V1.0\r\n
```

## 使用指南

### 1. 烧录固件

1. 从 [Releases](https://github.com/Hi-Barry/Pico-I2C-Bridge/releases) 下载最新的 `.uf2` 文件
2. 按住 BOOTSEL 按钮的同时连接 USB
3. 将 `.uf2` 文件复制到 RPI-RP2 大容量存储设备

### 2. 配置（可选）

开发期间可编辑 `boot.py` 启用 USB 磁盘：

```python
DEBUG_MODE = True  # 保留 USB 磁盘访问
```

### 3. 硬件连接

```
RP2040-Zero     I2C 设备
─────────       ─────────
GP2 (SDA)  ───  SDA
GP3 (SCL)  ───  SCL
GND        ───  GND
```

### 4. 串口通信

打开 CDC 串口（Linux: `/dev/ttyACM0`，Windows: `COM3`）并发送二进制命令：

```python
import serial

ser = serial.Serial('/dev/ttyACM0', 115200)

# 从设备 0x50 读取 5 字节，寄存器地址 0x02
ser.write(bytes([0xA1, 0x02, 0x05]))
data = ser.readline()
print(data)
```

## 错误码

| 错误码 | 说明 | 处理方法 |
|--------|------|----------|
| `ERR:NACK` | I2C 设备无响应 | 检查接线、设备供电 |
| `ERR:BUSY` | I2C 总线忙 | 稍后重试 |
| `ERR:NOBUS` | I2C 总线未初始化 | 重新连接设备 |
| `ERR:UNK` | 未知错误 | 查看日志 |

## LED 状态

| 颜色 | 状态 |
|------|------|
| 🟢 绿色（闪烁） | 正常运行，心跳指示 |
| 🔵 蓝色（常亮） | 正在处理数据 |
| 🔴 红色（常亮） | 致命错误，即将复位 |

## 开发

### 构建

```bash
# 安装 CircuitPython 依赖
pip install adafruit-circuitpython-neopixel

# 或使用 mpremote
mpremote mount .
mpremote run code.py
```

### 调试

启用控制台输出：

```python
# boot.py
usb_cdc.enable(console=True, data=True)
```

连接到控制台串口查看日志。

## 文件结构

```
pico-i2c-bridge/
├── boot.py              # 启动配置（USB CDC、存储设置）
├── code.py              # 主程序（I2C 桥接逻辑）
├── README.md            # 英文文档
├── docs/
│   └── README_zh.md     # 中文文档
└── LICENSE              # MIT 许可证
```

## 常见问题

### Q: 设备无法识别？

A: 确保已安装 [Adafruit CircuitPython UF2 Bootloader](https://circuitpython.org/board/raspberry_pi_pico/)。

### Q: I2C 读返回空数据？

A: 检查设备地址是否正确（7 位地址左移 1 位，读操作需 +1）。

### Q: 看门狗频繁复位？

A: 通信负载过高时可调大超时时间（`WATCHDOG_TIMEOUT = 10.0`）。

## 许可证

MIT License - 详见 [LICENSE](../LICENSE)。

## 致谢

- CircuitPython 团队为 RP2040 提供的优秀支持
- Seeed Studio 的 RP2040-Zero 开发板