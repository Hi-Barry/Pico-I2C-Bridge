# Pico I2C Bridge

[![GitHub release](https://img.shields.io/github/v/release/Hi-Barry/Pico-I2C-Bridge)](https://github.com/Hi-Barry/Pico-I2C-Bridge/releases)
[![License](https://img.shields.io/github/license/Hi-Barry/Pico-I2C-Bridge)](LICENSE)

A robust USB-to-I2C bridge firmware for Raspberry Pi Pico RP2040 (Seeed Studio RP2040-Zero), running on CircuitPython. Converts USB CDC serial commands to I2C bus transactions.

## Hardware

- **Board:** Seeed Studio XIAO RP2040 / RP2040-Zero
- **I2C Pins:** 
  - SDA: GP2
  - SCL: GP3
- **Status LED:** NeoPixel on GP16
- **USB:** Native USB CDC (virtual COM port)

## Features

- 🔌 **USB CDC Interface** - Virtual COM port, no driver needed
- 🔁 **I2C Bus Recovery** - Automatic detection and recovery from I2C bus lockups
- 🐕 **Watchdog Timer** - 5-second hardware watchdog prevents deadlocks
- 📦 **Memory Pre-allocation** - Fixed-size buffers avoid GC-induced latency
- 🚨 **Structured Error Codes** - `ERR:NACK`, `ERR:BUSY`, `ERR:NOBUS`, `ERR:UNK`
- 🔍 **Protocol Version Query** - Query firmware version via virtual address `0x00`
- 💡 **NeoPixel Status** - Visual feedback for connection and data activity

## Protocol

### Command Format

| Byte | Field | Description |
|------|-------|-------------|
| 0 | Address (8-bit) | I2C device address + R/W bit (LSB: 0=Write, 1=Read) |
| 1 | Register | Register address or command byte |
| 2+ | Data | Write payload or read length (for read operations) |

### Read Operation

```
Send: [0xA1, 0x05, 0x10]  # Read 16 bytes from device 0x50, register 0x05
Recv: [data...(16 bytes)]\r\n
```

### Write Operation

```
Send: [0xA0, 0x05, 0x12, 0x34]  # Write 0x1234 to device 0x50, register 0x05
Recv: \r\n  (success) or ERR:NACK\r\n
```

### Version Query

```
Send: [0x00, 0xFF]  # Virtual address 0x00, register 0xFF
Recv: V1.0\r\n
```

## Usage

### 1. Flash Firmware

1. Download the latest `.uf2` from [Releases](https://github.com/Hi-Barry/Pico-I2C-Bridge/releases)
2. Hold BOOTSEL button while connecting USB
3. Copy `.uf2` to the RPI-RP2 mass storage device

### 2. Configuration (Optional)

Edit `boot.py` to enable USB mass storage during development:

```python
DEBUG_MODE = True  # Keep USB drive accessible
```

### 3. Connect Hardware

```
RP2040-Zero     I2C Device
─────────       ─────────
GP2 (SDA)  ───  SDA
GP3 (SCL)  ───  SCL
GND        ───  GND
```

### 4. Serial Communication

Open the CDC serial port (e.g., `/dev/ttyACM0` on Linux, `COM3` on Windows) and send binary commands:

```python
import serial
ser = serial.Serial('/dev/ttyACM0', 115200)

# Read 5 bytes from device 0x50, register 0x02
ser.write(bytes([0xA1, 0x02, 0x05]))
data = ser.readline()
print(data)
```

## Error Codes

| Code | Description | Recovery |
|------|-------------|----------|
| `ERR:NACK` | I2C device did not acknowledge | Check wiring, device power |
| `ERR:BUSY` | I2C bus is locked | Wait and retry |
| `ERR:NOBUS` | I2C bus not initialized | Reconnect device |
| `ERR:UNK` | Unknown error | Check logs |

## LED Status

| Color | State |
|-------|-------|
| 🟢 Green (blinking) | Normal operation, heartbeat |
| 🔵 Blue (solid) | Processing data |
| 🔴 Red (solid) | Fatal error, resetting |

## Development

### Build

```bash
# Install CircuitPython dependencies
pip install adafruit-circuitpython-neopixel

# Or use mpremote
mpremote mount .
mpremote run code.py
```

### Debugging

Enable console output:

```python
# boot.py
usb_cdc.enable(console=True, data=True)
```

Connect to the console port to view logs.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- CircuitPython team for the excellent RP2040 support
- Seeed Studio for the RP2040-Zero board