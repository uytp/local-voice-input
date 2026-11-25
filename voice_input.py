# -*- coding: utf-8 -*-
"""
本地语音输入工具（SenseVoiceSmall · sherpa-onnx，完全离线）
用法一：按住“按住说话”按钮说话，松手出字（适合短话）。
用法二：点一下“按一下说话”按钮开始，说完再点一下停止并发送（适合长话）。
      识别结果会自动粘贴回你之前正在用的窗口（微信 / 其他 AI 等）。

模型文件位置（自动检测，无需联网）：
  ~/.dsh/speech-to-text/sensevoice/models/
    sensevoice-onnx/model.int8.onnx
    sensevoice-onnx/tokens.txt
"""

import os
import sys
import time
import queue
import threading
import traceback
import ctypes
from ctypes import wintypes

import numpy as np
import sherpa_onnx
import sounddevice as sd
import pyperclip
from pynput.keyboard import Key, Controller

# ================= 配置 =================
SAMPLE_RATE = 16000
MAX_SECONDS = 120        # 单次最长按住时间（秒），超时自动结束
USE_ITN = True           # 数字/单位归一化，如 “二十三年” -> “2023年”
NUM_THREADS = 2
PLAY_BEEP = True         # 开始/结束提示音

# 模型路径：优先用本目录下的 models/，其次用 ~/.dsh 下已下载的（DeepSeek 语音功能）
if getattr(sys, "frozen", False):
    # 打包成 exe 后，以 exe 所在目录为基准
    _HERE = os.path.dirname(sys.executable)
else:
    _HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_MODELS = os.path.join(_HERE, "models")
_DSH_MODELS = os.path.join(os.path.expanduser("~"), ".dsh", "speech-to-text", "sensevoice", "models")


def _pick(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]


SENSEVOICE_MODEL = _pick([
    os.path.join(_LOCAL_MODELS, "sensevoice-onnx", "model.int8.onnx"),
    os.path.join(_DSH_MODELS, "sensevoice-onnx", "model.int8.onnx"),
])
TOKENS = _pick([
    os.path.join(_LOCAL_MODELS, "sensevoice-onnx", "tokens.txt"),
    os.path.join(_DSH_MODELS, "sensevoice-onnx", "tokens.txt"),
])

def _log_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "VoiceInput")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


LOG_PATH = os.path.join(_log_dir(), "voice_input.log")
# ========================================

# 把输出写到日志，避免无窗口运行时丢失信息
_logf = open(LOG_PATH, "a", encoding="utf-8", buffering=1)


def log(msg):
    line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        _logf.write(line + "\n")
    except Exception:
        pass
    try:
        print(line)
    except Exception:
        pass


def beep(freq, ms):
    if not PLAY_BEEP:
        return
    try:
        import winsound
        winsound.Beep(freq, ms)
    except Exception:
        pass


# ================= 窗口焦点跟踪（用于把文字贴回原应用） =================
user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

_our_pid = os.getpid()
last_other_hwnd = None


def track_foreground():
    """记住最近一个不属于本程序的前台窗口（例如微信/别的 AI）。"""
    global last_other_hwnd
    try:
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            pid = wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value != _our_pid:
                last_other_hwnd = hwnd
    except Exception:
        pass


def refocus_last_window():
    """把焦点还给之前正在用的窗口；返回是否成功。"""
    if not last_other_hwnd:
        return False
    try:
        return bool(user32.SetForegroundWindow(last_other_hwnd))
    except Exception:
        return False


# ================= 状态 =================
lock = threading.Lock()
state = {"listening": False, "mode": None, "buffer": [], "start": 0.0}

recognizer = None
kb = Controller()


def transcribe(samples):
    s = recognizer.create_stream()
    s.accept_waveform(SAMPLE_RATE, samples)
    recognizer.decode_stream(s)
    return s.result.text.strip()


def paste(text):
    if not text:
        return
    pyperclip.copy(text)
    time.sleep(0.05)
    if not refocus_last_window():
        log("未能自动聚焦目标窗口，文字已复制到剪贴板")
        ui("status", "已复制文字，请手动 Ctrl+V 粘贴")
        return
    time.sleep(0.15)
    kb.press(Key.ctrl)
    kb.press("v")
    kb.release("v")
    kb.release(Key.ctrl)


def finalize_text(samples):
    if samples is None or len(samples) < int(SAMPLE_RATE * 0.12):
        ui("status", "待命（没听清，请重试）")
        ui("btn", False)
        return
    ui("status", "识别中…")
    try:
        text = transcribe(samples).strip()
    except Exception as e:
        log("transcribe error: %s" % e)
        ui("status", "识别出错，见日志")
        ui("btn", False)
        return
    ui("last", text if text else "（未识别出文字）")
    ui("status", "待命")
    ui("btn", False)
    if text:
        try:
            paste(text)
        except Exception as e:
            log("paste error: %s" % e)
        beep(660, 70)
        log("识别结果: %s" % text)


def start_session(mode="hold"):
    with lock:
        state["listening"] = True
        state["mode"] = mode
        state["buffer"] = []
        state["start"] = time.time()
    if mode == "toggle":
        ui("status", "录音中…（再点一下停止并发送）")
    else:
        ui("status", "录音中…（松开按钮结束）")
    beep(880, 100)


def stop_session():
    with lock:
        if not state["listening"]:
            return
        state["listening"] = False
        state["mode"] = None
        buf = state["buffer"]
        state["buffer"] = []
    samples = np.concatenate(buf) if buf else None
    threading.Thread(target=finalize_text, args=(samples,), daemon=True).start()


def audio_callback(indata, frames, time_info, status):
    with lock:
        if not state["listening"]:
            return
        state["buffer"].append(indata.reshape(-1).astype(np.float32) / 32768.0)
        if time.time() - state["start"] > MAX_SECONDS:
            state["listening"] = False
            state["mode"] = None
            buf = state["buffer"]
            state["buffer"] = []
            overflow = True
        else:
            overflow = False
    if overflow:
        samples = np.concatenate(buf) if buf else None
        threading.Thread(target=finalize_text, args=(samples,), daemon=True).start()


# ================= UI =================
ui_q = queue.Queue()


def ui(kind, val):
    ui_q.put((kind, val))
    log("UI %s: %s" % (kind, val))


def build_ui():
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("语音输入 · 本地 SenseVoice")
    root.geometry("430x270+60+60")
    root.attributes("-topmost", True)
    try:
        root.attributes("-toolwindow", True)
    except Exception:
        pass

    status_var = tk.StringVar(value="启动中…")
    last_var = tk.StringVar(value="（还没有内容）")

    # 按钮一：按住说话（长按，松手出字）
    hold_btn = tk.Button(root, text="按住说话", font=("Microsoft YaHei", 15, "bold"),
                         height=2, bg="#4CAF50", fg="white", activebackground="#388E3C",
                         activeforeground="white", relief="flat", cursor="hand2", takefocus=0)
    hold_btn.pack(fill="x", padx=12, pady=(10, 4))

    # 按钮二：按一下说话 / 再按一下停止（点按，适合说长话）
    toggle_btn = tk.Button(root, text="按一下说话（说长话用）", font=("Microsoft YaHei", 15, "bold"),
                           height=2, bg="#1976D2", fg="white", activebackground="#1565C0",
                           activeforeground="white", relief="flat", cursor="hand2", takefocus=0)
    toggle_btn.pack(fill="x", padx=12, pady=(0, 6))

    tk.Label(root, textvariable=status_var, font=("Microsoft YaHei", 12, "bold"), fg="#0a7d33").pack(
        anchor="w", padx=12, pady=(2, 0))
    tk.Label(root, text="最近识别：", font=("Microsoft YaHei", 9), fg="#888").pack(
        anchor="w", padx=12, pady=(6, 0))
    tk.Label(root, textvariable=last_var, font=("Microsoft YaHei", 10),
             wraplength=400, justify="left", anchor="nw").pack(
        anchor="w", padx=12, fill="both", expand=True)

    def refresh_buttons():
        with lock:
            listening = state["listening"]
            mode = state["mode"]
        if listening and mode == "hold":
            hold_btn.config(text="松开结束", bg="#e53935", activebackground="#c62828", state="normal")
            toggle_btn.config(state="disabled")
        elif listening and mode == "toggle":
            toggle_btn.config(text="停止并发送", bg="#e53935", activebackground="#c62828", state="normal")
            hold_btn.config(state="disabled")
        else:
            hold_btn.config(text="按住说话", bg="#4CAF50", activebackground="#388E3C", state="normal")
            toggle_btn.config(text="按一下说话（说长话用）", bg="#1976D2", activebackground="#1565C0", state="normal")
            try:
                hold_btn.grab_release()
            except Exception:
                pass

    def on_hold_press(e):
        with lock:
            if state["listening"]:
                return  # 已在录音（点按模式），忽略
        try:
            hold_btn.grab_set_global()
        except Exception:
            pass
        start_session("hold")
        refresh_buttons()

    def on_hold_release(e):
        with lock:
            if not state["listening"] or state["mode"] != "hold":
                return
        stop_session()
        refresh_buttons()

    def on_toggle_click():
        with lock:
            if state["listening"]:
                do_start = False
                do_stop = (state["mode"] == "toggle")
            else:
                do_start = True
                do_stop = False
        if do_start:
            start_session("toggle")
            refresh_buttons()
        elif do_stop:
            stop_session()
            refresh_buttons()

    hold_btn.bind("<ButtonPress-1>", on_hold_press)
    hold_btn.bind("<ButtonRelease-1>", on_hold_release)
    toggle_btn.config(command=on_toggle_click)

    def poll_ui():
        track_foreground()
        try:
            while True:
                kind, val = ui_q.get_nowait()
                if kind == "status":
                    status_var.set(val)
                elif kind == "last":
                    last_var.set(val)
                elif kind == "btn":
                    refresh_buttons()
                elif kind == "error":
                    status_var.set("出错：" + val)
                    messagebox.showerror("语音输入", val)
        except queue.Empty:
            pass
        root.after(60, poll_ui)

    root.after(60, poll_ui)
    return root


def init_background():
    """在后台线程做耗时的模型加载与设备初始化。"""
    global recognizer
    try:
        missing = [p for p in (SENSEVOICE_MODEL, TOKENS) if not os.path.exists(p)]
        if missing:
            ui("error", "找不到本地语音模型文件：\n" + "\n".join(missing) +
               "\n\n请确认之前已经用 DeepSeek 的语音功能下载过模型。")
            return

        ui("status", "正在加载模型…")
        recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=SENSEVOICE_MODEL,
            tokens=TOKENS,
            num_threads=NUM_THREADS,
            use_itn=USE_ITN,
            debug=False,
        )
        log("模型加载完成")

        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                callback=audio_callback)
        stream.start()
        log("麦克风已就绪")

        ui("status", "待命 · 按住或点按说话")
    except Exception as e:
        log("初始化失败：%s\n%s" % (e, traceback.format_exc()))
        ui("error", "初始化失败：%s\n\n详情见 voice_input.log" % e)


def main():
    root = build_ui()
    threading.Thread(target=init_background, daemon=True).start()
    try:
        root.mainloop()
    finally:
        log("退出")
        try:
            _logf.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
