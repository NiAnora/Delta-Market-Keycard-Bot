import json
import pyautogui
import time
from PIL import Image
import os
import keyboard
import datetime
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from paddleocr import PaddleOCR

# 禁用PaddleOCR调试日志
os.environ["PPOCR_LOG_LEVEL"] = "ERROR"
logging.getLogger("ppocr").setLevel(logging.ERROR)

# 常量定义 - 修改路径处理方式
try:
    SCRIPT_DIR = Path(__file__).parent.resolve()
    CONFIG_PATH = (SCRIPT_DIR / "../config/config.json").resolve()  # 向上一级到assets目录
    IMAGES_DIR = SCRIPT_DIR / "images"
    LOGS_FILE = SCRIPT_DIR / "logs.txt"
    
    # 打印路径用于调试
    print(f"脚本目录: {SCRIPT_DIR}")
    print(f"配置文件路径: {CONFIG_PATH}")
    print(f"确保配置文件存在: {CONFIG_PATH.exists()}")
except Exception as e:
    logging.error(f"路径初始化错误: {str(e)}")
    raise

# 全局变量
is_loop: bool = False  # 是否循环执行
is_debug: bool = True  # 调试模式
is_running: bool = False  # 是否正在运行
screen_width, screen_height = pyautogui.size()  # 屏幕尺寸

# 初始化OCR模型
ocr_chinese = PaddleOCR(use_angle_cls=True, lang='ch')  # 中文OCR模型
ocr_english = PaddleOCR(use_angle_cls=True, lang='en')  # 英文OCR模型(用于数字识别)


class ConfigManager:
    """配置管理器"""
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"配置文件 {CONFIG_PATH} 不存在")
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"配置文件 {CONFIG_PATH} 格式错误: {e}")
            return {}
        except Exception as e:
            logging.error(f"读取配置时发生未知错误: {str(e)}")
            return {}

    @staticmethod
    def get_region(config: Dict[str, Any], key: str) -> Optional[Tuple[int, int, int, int]]:
        """从配置中获取区域坐标"""
        region = config.get(key)
        if not region or len(region) != 4:
            logging.error(f"配置中缺少有效的 {key} 字段")
            return None
        return tuple(region)


class ScreenshotHelper:
    """截图辅助类"""
    
    @staticmethod
    def ensure_dir_exists(directory: Path) -> None:
        """确保目录存在"""
        directory.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def take_screenshot(region: Tuple[int, int, int, int], threshold: int) -> Optional[Image.Image]:
        """截取指定区域的截图并二值化"""
        try:
            screenshot = pyautogui.screenshot(region=region)
            gray_image = screenshot.convert('L')  # 转为灰度图
            # 二值化处理
            binary_image = gray_image.point(lambda p: 255 if p > threshold else 0)
            binary_image = Image.eval(binary_image, lambda x: 255 - x)  # 反色
            return binary_image
        except Exception as e:
            logging.error(f"截图失败: {str(e)}")
            return None


class CardProcessor:
    """门卡处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # 购买按钮位置(默认值: 屏幕宽度82.5%, 高度86%)
        self.purchase_btn_location = config.get("purchase_btn_location", [0.825, 0.86])
    
    def get_card_price(self) -> Optional[int]:
        """获取当前门卡价格(仅识别数字)"""
        region = ConfigManager.get_region(self.config, "card_price_range")
        if not region:
            return None

        # 截取并处理价格区域图像
        image = ScreenshotHelper.take_screenshot(region=region, threshold=55)
        if not image:
            return None

        # 保存价格截图
        ScreenshotHelper.ensure_dir_exists(IMAGES_DIR)
        price_image_path = IMAGES_DIR / "card_price.png"
        image.save(price_image_path)
        
        # 使用英文OCR识别价格
        result = ocr_english.ocr(str(price_image_path), cls=False)
        if not result or not result[0]:
            logging.warning("无法识别价格")
            return None

        # 提取识别文本
        text = result[0][0][1][0]  # 获取第一个识别结果的文字部分
        if is_debug:
            print(f"提取的门卡原始价格文本: {text}")

        # 只保留数字字符
        digits = ''.join(filter(str.isdigit, text))
        if not digits:
            logging.warning("未识别到有效数字")
            return None

        try:
            return int(digits)
        except ValueError:
            logging.warning("无法解析价格")
            return None
    
    def get_card_name(self) -> Optional[str]:
        """获取当前门卡名称"""
        region = ConfigManager.get_region(self.config, "card_name_range")
        if not region:
            return None

        # 截取门卡名称区域
        screenshot = ScreenshotHelper.take_screenshot(region=region, threshold=100)
        if not screenshot:
            return None

        # 保存名称截图
        ScreenshotHelper.ensure_dir_exists(IMAGES_DIR)
        name_image_path = IMAGES_DIR / "card_name.png"
        screenshot.save(name_image_path)
        
        # 使用中文OCR识别门卡名称
        result = ocr_chinese.ocr(str(name_image_path), cls=True)
        if not result or not result[0]:
            logging.warning("无法识别门卡名称")
            return None

        # 提取并处理识别文本
        text = result[0][0][1][0]  # 获取第一个识别结果的文字部分
        return text.replace(" ", "").strip()  # 去除空格和空白字符
    
    @staticmethod
    def log_purchase(card_name: str, ideal_price: int, price: int, premium: float) -> None:
        """记录购买信息到日志文件"""
        log_entry = (
            f"购买时间: {datetime.datetime.now():%Y-%m-%d %H:%M:%S} | "
            f"门卡名称: {card_name} | "
            f"理想价格: {ideal_price} | "
            f"购买价格: {price} | "
            f"溢价: {premium:.2f}%\n"
        )
        with open(LOGS_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
    
    def price_check_flow(self, card_info: Dict[str, Any]) -> bool:
        """价格检查主流程"""
        position = card_info.get('position')
        if not position or len(position) != 2:
            logging.error(f"门卡 {card_info.get('name')} 的position配置无效")
            return False

        # 移动到门卡位置并点击
        x, y = position[0] * screen_width, position[1] * screen_height
        pyautogui.moveTo(x, y)
        pyautogui.click()
        time.sleep(0.1)  # 短暂等待

        # 获取门卡名称
        card_name = self.get_card_name()
        if not card_name:
            logging.warning("无法获取门卡名称，跳过本次检查")
            pyautogui.press('esc')  # 退出当前界面
            return False

        # 获取门卡价格
        current_price = self.get_card_price()
        if current_price is None:
            logging.warning("无法获取有效价格，跳过本次检查")
            pyautogui.press('esc')
            return False

        # 计算价格阈值和溢价率
        floating_percentage_range = card_info.get('floating_percentage_range', 0.1)
        ideal_price = card_info.get('ideal_price', 0)
        max_price = ideal_price + (ideal_price * floating_percentage_range)
        premium = ((current_price / ideal_price) - 1) * 100

        # 验证门卡名称是否匹配
        if card_name not in card_info.get("name", []):
            logging.warning(
                f"识别到的门卡名称: {card_name}, "
                f"需要购买的门卡名称: {card_info.get('name')}, "
                "门卡不匹配"
            )
            pyautogui.press('esc')
            return False

        # 打印价格信息
        print(
            f"理想价格: {ideal_price} | "
            f"最高可接受价格: {max_price} | "
            f"当前价格: {current_price} | "
            f"溢价率: {premium:.2f}%"
        )

        # 价格检查逻辑
        if premium < 0 or current_price < max_price:
            # 移动到购买按钮位置
            btn_x = screen_width * self.purchase_btn_location[0]
            btn_y = screen_height * self.purchase_btn_location[1]
            pyautogui.moveTo(btn_x, btn_y)
            
            # 如果不是调试模式，则实际点击购买
            if not is_debug:
                pyautogui.click()
            
            # 记录购买日志
            self.log_purchase(card_name, ideal_price, current_price, premium)
            pyautogui.press('esc')  # 退出当前界面
            return True
        
        logging.info("价格过高，取消购买")
        pyautogui.press('esc')
        return False


def set_running_state(state: bool) -> None:
    """设置运行状态"""
    global is_running
    is_running = state
    status = "开始" if state else "停止"
    print(f"{status}循环执行")


def main():
    global is_loop, is_debug, is_running
    
    # 加载配置文件
    config = ConfigManager.load_config()
    if not config:
        return
    
    # 更新全局配置
    is_debug = config.get("is_debug", True)
    is_loop = config.get("is_loop", False)
    
    # 获取需要购买的门卡列表
    keys_config = config.get("keys", [])
    cards_to_buy = [card for card in keys_config if card.get('want_buy', 0) == 1]
    if not cards_to_buy:
        print("没有需要购买的门卡，程序退出")
        return
    
    # 初始化门卡处理器
    processor = CardProcessor(config)
    
    # 设置热键
    keyboard.add_hotkey('f8', lambda: set_running_state(True))
    keyboard.add_hotkey('f9', lambda: set_running_state(False))
    print("按 F8 开始循环，按 F9 停止循环")

    # 主循环
    while True:
        if is_running:
            # 使用副本遍历以便安全删除元素
            for card_info in cards_to_buy.copy():  
                if not is_running:
                    break
                
                print(f"正在检查门卡: {card_info['name']}")
                if processor.price_check_flow(card_info):
                    # 如果不是循环模式，则从购买列表中移除
                    if not is_loop:
                        cards_to_buy.remove(card_info)
                    print(f"剩余待购买门卡: {[card['name'] for card in cards_to_buy]}")
                time.sleep(0.1)  # 短暂间隔
        else:
            time.sleep(0.1)  # 非运行状态时降低CPU占用


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR:{str(e)}")
    finally:
        # 输出最终配置结果
        with open(CONFIG_FILE, 'r') as f:
            print("CONFIG_RESULT:" + json.dumps(json.load(f)))