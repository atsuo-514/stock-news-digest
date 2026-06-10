"""pytest 設定: src/ を import パスに追加（`import fetch` 等を可能にする）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
