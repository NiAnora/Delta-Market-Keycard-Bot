import pyautogui
import keyboard
import json
import sys
import numpy as np
import cv2
from PIL import ImageGrab
from pathlib import Path

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
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"keys": [{}]}

def save_config(config):
    """保存配置文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def select_position():
    """通过鼠标点击选择屏幕位置"""
    screenshot = np.array(ImageGrab.grab())
    darkened = cv2.addWeighted(screenshot, 0.7, np.zeros_like(screenshot), 0.3, 0)
    
    cv2.namedWindow("Position Selector", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("Position Selector", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    position = None
    
    def on_mouse(event, x, y, flags, param):
        nonlocal position
        if event == cv2.EVENT_LBUTTONDOWN:
            position = (x, y)
    
    cv2.setMouseCallback("Position Selector", on_mouse)
    
    while position is None:
        display_img = darkened.copy()
        cv2.imshow("Position Selector", display_img)
        
        if cv2.waitKey(10) == 27 or keyboard.is_pressed('esc'):
            break
    
    cv2.destroyAllWindows()
    
    if position:
        screen_width, screen_height = pyautogui.size()
        return [
            round(position[0] / screen_width, 4),
            round(position[1] / screen_height, 4)
        ]
    return None

def main():
    """主函数"""
    output = {"success": False}
    config = load_config()
    
    try:
        new_position = select_position()
        if not new_position:
            output["error"] = "用户取消选择"
            return output
            
        if not config.get('keys'):
            config['keys'] = [{}]
        config['keys'][0]['position'] = new_position
        save_config(config)
        
        output.update({
            "success": True,
            "position": new_position,
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
