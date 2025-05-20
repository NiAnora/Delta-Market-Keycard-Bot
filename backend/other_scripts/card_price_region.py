import pyautogui
import keyboard
import json
import sys
import numpy as np
import cv2
from pathlib import Path
from PIL import ImageGrab

if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)

# 初始化路径
SCRIPT_FILE = Path(__file__).resolve()
BASE_DIR = SCRIPT_FILE.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# 设置pyautogui参数
pyautogui.PAUSE = 0.1
pyautogui.FAILSAFE = True

def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "is_loop": False,
            "is_debug": True,
            "card_name_range": [0, 0, 0, 0],
            "card_price_range": [0, 0, 0, 0],
            "keys": []
        }

def save_config(config):
    """保存配置文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def select_region():
    """选择屏幕区域"""
    screenshot = np.array(ImageGrab.grab())
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
            selection = [min(x1, x2), min(y1, y2), abs(x2-x1), abs(y2-y1)]
    
    cv2.setMouseCallback("Region Selector", on_mouse)
    
    while True:
        display_img = darkened.copy()
        
        if start_pos and current_pos:
            x1, y1 = start_pos
            x2, y2 = current_pos
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            
            display_img[y1:y2, x1:x2] = screenshot[y1:y2, x1:x2]
            cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        
        cv2.imshow("Region Selector", display_img)
        
        if selection is not None:
            break
        if cv2.waitKey(10) == 27 or keyboard.is_pressed('esc'):
            break
    
    cv2.destroyAllWindows()
    return selection

def main():
    """主函数"""
    output = {"success": False}
    config = load_config()
    
    try:
        region = select_region()
        if not region:
            output["error"] = "用户取消选择"
            return output
            
        config["card_price_range"] = region
        save_config(config)
        
        output.update({
            "success": True,
            "region": region,
            "config": config
        })
        
    except Exception as e:
        output["error"] = str(e)
    
    sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")
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
