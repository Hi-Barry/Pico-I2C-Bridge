import usb_cdc
import storage

# 开发模式：设为 True 保留 USB 磁盘，方便拖放更新代码
# 生产模式：设为 False 禁用 USB 磁盘，释放为 CDC 数据口
DEBUG_MODE = False

if not DEBUG_MODE:
    storage.disable_usb_drive()

usb_cdc.enable(console=True, data=True)