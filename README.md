# Werm

![Werm Icon](Werm_Icon.jpg)

A modern, privacy-conscious browser with integrated AI features that work seamlessly in the background without cluttering your interface or forcing unwanted interactions.

## Overview

Werm is a Python-based desktop browser built on PySide6 that brings AI capabilities to your browsing experience in an elegant, non-intrusive way. Unlike traditional browsers that prioritize AI features, Werm puts **you** in control—AI enhancements are available when you need them, never forced upon you.

## Features

- 🌐 **Full-Featured Browser** – Modern web browsing with WebEngine support
- 🤖 **Passive AI Integration** – AI features available without being shoved in your face
- 🔒 **Privacy-First Design** – Control over what data AI processes
- ⚡ **Lightweight & Fast** – Built with PySide6 for responsive performance
- 🛠️ **Intelligent Assistance** – AI-powered features work in the background
- 📡 **Network Aware** – Smart handling of connections and requests

## Getting Started

### Prerequisites

- Python 3.8 or higher
- PySide6

### Installation

1. Clone the repository:
```bash
git clone https://github.com/umm-dev/Werm.git
cd Werm
```

2. Install dependencies:
```bash
pip install PySide6
```

3. Run Werm:
```bash
python main.py
```

## Usage

Once Werm launches, use it like any standard browser:

```bash
python main.py
```

**Key Differences:**
- AI features integrate seamlessly without pop-ups or persistent panels
- Hover over or right-click for intelligent suggestions (when available)
- AI processing happens quietly in the background
- Control which AI features are active through minimal, unobtrusive settings

## Technical Stack

### Core Dependencies

```
os              – System operations
sys             – System utilities
json            – Configuration and data handling
time            – Timing operations
dataclasses     – Data structure definitions
typing          – Type hints for code clarity
urllib.parse    – URL parsing and manipulation
```

### PySide6 Components

```
PySide6.QtCore           – Core framework
PySide6.QtGui            – GUI elements and styling
PySide6.QtWidgets        – Widget library
PySide6.QtWebEngineWidgets  – Browser widget
PySide6.QtWebEngineCore  – WebEngine functionality
PySide6.QtNetwork        – Network operations
```

## Project Structure

```
Werm/
├── main.py                  # Main application entry point
├── Werm_Icon.jpg           # Application icon
├── LICENSE                 # License information
└── README.md               # This file
```

## Philosophy

Werm is built on the principle that **AI should enhance, not intrude**. Our approach:

- ✅ AI works when you need it
- ✅ No forced notifications or suggestions
- ✅ Clean, minimal interface
- ✅ User remains in control
- ✅ Features available on-demand

## Contributing

Contributions are welcome! Whether you're improving the browser core or enhancing AI integration, please submit a Pull Request. We're especially interested in:

- UI/UX improvements
- New passive AI features
- Performance optimizations
- Bug fixes and stability improvements

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Support

For issues, questions, or feature suggestions, please open an issue on the [GitHub repository](https://github.com/umm-dev/Werm/issues).

---

**Browse smarter. Not louder. 🧠✨**
