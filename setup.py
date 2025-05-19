from setuptools import setup

APP = ['google_chat_viewer.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'includes': ['tkinter', 'ttkbootstrap'],
    'packages': ['ttkbootstrap'],
    'plist': {
        'CFBundleName': 'Google Chat Viewer',
        'CFBundleDisplayName': 'Google Chat Viewer (KST)',
        'CFBundleIdentifier': 'com.yourname.googlechatviewer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
    },
    # 'iconfile': 'your_icon.icns',  # 원하면 아이콘도 추가 가능
}

setup(
    app=APP,
    name='Google Chat Viewer',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)