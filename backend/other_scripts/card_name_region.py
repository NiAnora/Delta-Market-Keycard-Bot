import pyautogui
import keyboard
import json
import time
from pathlib import Path
import sys
import numpy as np
import cv2
from PIL import ImageGrab
import pytesseract
from pytesseract import Output

if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)

# 确保 __file__ 是脚本文件的路径
SCRIPT_FILE = Path(__file__).resolve()

# 定义 BASE_DIR
BASE_DIR = SCRIPT_FILE.parent.parent.parent  # 向上三级到项目根目录

# 定义 CONFIG_DIR 和 CONFIG_FILE
CONFIG_DIR = BASE_DIR / "config"  # 指向 assets/config 目录
CONFIG_FILE = CONFIG_DIR / "config.json"

# 确保 TEMP_DIR 存在
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

pyautogui.PAUSE = 0.1
pyautogui.FAILSAFE = True

def load_config(file_path=CONFIG_FILE):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "is_loop": False,
            "is_debug": True,
            "card_name_range": [0, 0, 0, 0],
            "card_price_range": [0, 0, 0, 0],
            "keys": []
        }

def save_config(config, file_path=CONFIG_FILE):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def select_region_with_drag(region_name):
    screenshot = np.array(ImageGrab.grab())
    original_h, original_w = screenshot.shape[:2]
    darkened = cv2.addWeighted(screenshot, 0.7, np.zeros_like(screenshot), 0.3, 0)
    cv2.namedWindow("Region Selector", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Region Selector", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    selecting = False
    start_pos = None
    current_pos = None
    selection = None
    
    def on_mouse(event, x, y, flags, param):
        nonlocal selecting, start_pos, current_pos, selection
        
        if event == cv2.EVENT_LBUTTONDOWN:
            selecting = True
            start_pos = (x, y)
            current_pos = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            if selecting:
                current_pos = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            selecting = False
            current_pos = (x, y)
            x1, y1 = start_pos
            x2, y2 = current_pos
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
            selection = [x1, y1, x2-x1, y2-y1]
    
    cv2.setMouseCallback("Region Selector", on_mouse)
    
    while True:
        display_img = darkened.copy()
        
        if start_pos and current_pos:
            x1, y1 = start_pos
            x2, y2 = current_pos
            
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
                
            display_img[y1:y2, x1:x2] = screenshot[y1:y2, x1:x2]
            cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        
        cv2.imshow("Region Selector", display_img)
        
        if selection is not None:
            break
        if cv2.waitKey(10) == 27 or keyboard.is_pressed('esc'):
            break
    
    cv2.destroyAllWindows()
    return selection

def capture_and_ocr(config):
    x, y, w, h = config["card_name_range"]
    screenshot = ImageGrab.grab(bbox=(x, y, x+w, y+h))
    screenshot_path = TEMP_DIR / "card_name_range.png"
    screenshot.save(screenshot_path)
    
    try:
        custom_config = r'--oem 3 --psm 6 -l chi_sim'
        text = pytesseract.image_to_string(screenshot, config=custom_config)
        cleaned_text = text.replace(" ", "").replace("\n", "")
        return cleaned_text
    except Exception as e:
        return None

def main():
    config = load_config()
    output = {"success": False}
    
    try:
        region = select_region_with_drag("名称区域")
        if not region:
            output["error"] = "用户取消选择"
            return output
            
        config["card_name_range"] = region
        ocr_text = capture_and_ocr(config)
        
        # ✅ 关键优化：更新 keys 最后一个元素的 name 字段
        if "keys" not in config or not isinstance(config["keys"], list):
            config["keys"] = []  # 初始化 keys 为列表
        
        if not config["keys"]:
            # 如果 keys 为空，添加一个完整结构的字典
            config["keys"].append({
                "name": ocr_text,
                "floating_percentage_range": 0.22,
                "ideal_price": 200004,
                "position": [0.6891, 0.5519],
                "want_buy": 1
            })
        else:
            # 直接更新最后一个元素的 name 字段
            last_key = config["keys"][-1]
            last_key["name"] = ocr_text
        
        # 保存配置
        save_config(config)
        
        output.update({
            "success": True,
            "region": region,
            "ocr_text": ocr_text,
            "config": config
        })
        
    except Exception as e:
        output["error"] = str(e)
    
    sys.stdout.write(json.dumps(output) + "\n")
    sys.stdout.flush()
    return output

if __name__ == "__main__":
    try:
        result = main()
        exit_code = 0 if result.get("success") else 1
    except Exception as e:
        sys.stdout.write(json.dumps({"success": False, "error": str(e)}) + "\n")
        exit_code = 1
    finally:
        sys.exit(exit_code)