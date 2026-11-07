"""
ST77922 内置触摸（LCDWIKI ES3C35P 3.5" 板）

这颗芯片是 TDDI（触显一体）：显示和电容触摸在同一个 die 里，触摸走独立的
I2C 从机地址 0x55，寄存器地址 16 位、大端。

协议要点（来源：厂家例程 / xiaozhi-esp32 lcdwiki-es3c35p 移植）：
  - 0x0010  状态，bit3 = 0x08 表示有触摸
  - 0x0014  点数据，每点 7 字节，必须一次性读完 7×点数才能清空缓冲
            byte0: bit7=有效，bit0~5 = X 高 6 位
            byte1: X 低 8 位
            byte2: bit0~5 = Y 高 6 位
            byte3: Y 低 8 位
            byte4: 压力/重量
  - 不支持中断上报的可靠方式，厂家也是轮询（约 30fps）
"""

from esphome import pins
import esphome.codegen as cg
from esphome.components import i2c, touchscreen
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_INTERRUPT_PIN, CONF_RESET_PIN
from esphome.types import ConfigType

DEPENDENCIES = ["i2c"]
AUTO_LOAD = ["touchscreen"]

st77922_touch_ns = cg.esphome_ns.namespace("st77922_touch")
ST77922Touchscreen = st77922_touch_ns.class_(
    "ST77922Touchscreen",
    touchscreen.Touchscreen,
    i2c.I2CDevice,
)

CONFIG_SCHEMA = touchscreen.TOUCHSCREEN_SCHEMA.extend(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(ST77922Touchscreen),
            cv.Optional(CONF_INTERRUPT_PIN): pins.internal_gpio_input_pin_schema,
            cv.Optional(CONF_RESET_PIN): pins.gpio_output_pin_schema,
        }
    ).extend(i2c.i2c_device_schema(0x55))
)


async def to_code(config: ConfigType) -> None:
    var = cg.new_Pvariable(config[CONF_ID])
    await touchscreen.register_touchscreen(var, config)
    await i2c.register_i2c_device(var, config)

    if reset_pin_config := config.get(CONF_RESET_PIN):
        reset_pin = await cg.gpio_pin_expression(reset_pin_config)
        cg.add(var.set_reset_pin(reset_pin))

    if interrupt_pin_config := config.get(CONF_INTERRUPT_PIN):
        interrupt_pin = await cg.gpio_pin_expression(interrupt_pin_config)
        cg.add(var.set_interrupt_pin(interrupt_pin))
