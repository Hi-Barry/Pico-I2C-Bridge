import board
import busio
import usb_cdc
import time
import microcontroller
import neopixel
import gc
from digitalio import DigitalInOut, Direction, Pull

# ================= 配置区域 =================
SDA_PIN = board.GP2
SCL_PIN = board.GP3
I2C_FREQUENCY = 400_000 
WATCHDOG_TIMEOUT = 5.0
MAX_CMD_SIZE = 256   # 最大接收命令长度
MAX_I2C_SIZE = 256   # 最大 I2C 读取长度
# 虚拟地址：协议版本查询
PROTO_VERSION = b"V1.0\r\n"

# ================= 初始化 =================

# 1. 预分配内存缓冲区（收发隔离，避免重叠）
_cmd_buffer = bytearray(MAX_CMD_SIZE + 5)
_i2c_buffer = bytearray(MAX_I2C_SIZE)
cmd_view = memoryview(_cmd_buffer)
i2c_view = memoryview(_i2c_buffer)

# 2. NeoPixel 初始化
try:
    pixel = neopixel.NeoPixel(board.GP16, 1, brightness=0.2, auto_write=True)
    pixel[0] = (0, 0, 0)
except Exception:
    pixel = None

# 3. 看门狗初始化
wdt = None
try:
    import watchdog
    wdt = microcontroller.watchdog
    wdt.timeout = WATCHDOG_TIMEOUT
    wdt.mode = watchdog.WatchDogMode.RESET
except Exception:
    pass

serial = usb_cdc.data

# I2C 总线重建标记
_i2c_needs_rebuild = False

def force_i2c_bus_unlock():
    """
    I2C 总线死锁恢复逻辑。
    如果从机死机拉低 SDA，手动翻转 SCL 9次以释放总线。
    """
    try:
        p_scl = DigitalInOut(SCL_PIN)
        p_sda = DigitalInOut(SDA_PIN)
        p_scl.direction = Direction.OUTPUT
        p_sda.direction = Direction.INPUT

        if p_sda.value:
            p_scl.deinit()
            p_sda.deinit()
            return

        for _ in range(9):
            p_scl.value = False
            time.sleep(0.00001)
            p_scl.value = True
            time.sleep(0.00001)

        p_scl.deinit()
        p_sda.deinit()
    except Exception as e:
        print(f"Unlock retry failed: {e}")

def get_i2c_bus():
    """初始化 I2C 总线，包含故障恢复"""
    bus = None
    try:
        bus = busio.I2C(SCL_PIN, SDA_PIN, frequency=I2C_FREQUENCY)
        return bus
    except RuntimeError:
        print("I2C Bus Init Failed, trying to unlock...")
        force_i2c_bus_unlock()
        try:
            bus = busio.I2C(SCL_PIN, SDA_PIN, frequency=I2C_FREQUENCY)
            print("I2C Bus Recovered.")
            return bus
        except Exception as e:
            print(f"I2C Init Fatal Error: {e}")
            return None
    except Exception as e:
        print(f"I2C Init Error: {e}")
        return None

def process_serial_command(i2c, data_view):
    """
    解析并执行 I2C 命令
    协议格式：[addr_8bit, register, data...]
    - addr_8bit 最低位：0=写，1=读
    - 读操作：[addr_8bit|0x01, register, read_length]
    - 写操作：[addr_8bit&0xFE, register, data...]
    """
    global _i2c_needs_rebuild

    if len(data_view) < 3:
        return 

    device_addr_8bit = data_view[0]
    device_addr_7bit = device_addr_8bit >> 1
    is_read_op = (device_addr_8bit & 0x01) == 0x01
    register = data_view[1]

    # 虚拟地址 0x00：协议版本查询
    if device_addr_7bit == 0x00 and register == 0xFF:
        if serial:
            serial.write(PROTO_VERSION)
        return

    if i2c is None:
        if serial: serial.write(b"ERR:NOBUS\r\n")
        return

    if not i2c.try_lock():
        if serial: serial.write(b"ERR:BUSY\r\n")
        return

    try:
        if is_read_op:
            # === 读取操作 ===
            read_length = data_view[2]
            if read_length == 0 or read_length > MAX_I2C_SIZE:
                read_length = 1 

            # 使用独立的 i2c_view，不会覆盖 cmd_view
            i2c.writeto_then_readfrom(device_addr_7bit, bytes([register]), i2c_view[:read_length])

            if serial:
                serial.write(i2c_view[:read_length])
                serial.write(b"\r\n")

        else:
            # === 写入操作 ===
            # payload 包含 [register, data...]，writeto 会将 register 作为首字节发送
            payload = data_view[1:] 
            i2c.writeto(device_addr_7bit, payload)

    except OSError:
        # I2C NACK（设备未响应）
        _i2c_needs_rebuild = True
        if serial: serial.write(b"ERR:NACK\r\n")
    except Exception:
        _i2c_needs_rebuild = True
        if serial: serial.write(b"ERR:UNK\r\n")
    finally:
        i2c.unlock()

def main():
    global _i2c_needs_rebuild

    print("I2C Bridge Started (Robust Mode).")

    i2c = get_i2c_bus()
    last_time = time.monotonic()
    last_gc_time = time.monotonic()
    led_state = False

    while True:
        # 1. 喂狗
        if wdt: wdt.feed()

        current_time = time.monotonic()

        # 2. 定期垃圾回收（每 3 秒）
        if current_time - last_gc_time > 3.0:
            gc.collect()
            last_gc_time = current_time

        # 3. LED 心跳 & 连接检查
        if current_time - last_time > 0.5:
            led_state = not led_state
            if pixel: pixel[0] = (0, 255, 0) if led_state else (0, 0, 0)
            last_time = current_time

            # 掉线自动重连
            if i2c is None:
                i2c = get_i2c_bus()

        # 4. I2C 运行时损坏重建
        if _i2c_needs_rebuild:
            _i2c_needs_rebuild = False
            try:
                i2c.deinit()
            except:
                pass
            i2c = get_i2c_bus()

        # 5. 串口数据接收
        if serial and serial.in_waiting > 0:
            try:
                if pixel: pixel[0] = (0, 0, 255)

                if serial.in_waiting < 3:
                    time.sleep(0.002) 
                    if wdt: wdt.feed()

                bytes_available = serial.in_waiting
                count = min(bytes_available, MAX_CMD_SIZE)

                # 带喂狗的读取，防止阻塞导致看门狗复位
                received = 0
                while received < count:
                    chunk = serial.readinto(cmd_view[received:received + min(32, count - received)])
                    if chunk is None or chunk == 0:
                        break
                    received += chunk
                    if wdt: wdt.feed()

                if received > 0:
                    data_view = cmd_view[:received]
                    process_serial_command(i2c, data_view)

                if pixel: pixel[0] = (0, 255, 0) if led_state else (0, 0, 0)

            except Exception:
                pass

        time.sleep(0.0001)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        if 'pixel' in locals() and pixel:
            pixel[0] = (255, 0, 0)
        time.sleep(5)
        microcontroller.reset()