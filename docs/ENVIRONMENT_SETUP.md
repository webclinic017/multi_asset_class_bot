# Environment Setup Guide

## Problem Solved ✅

The original issue was that the system was trying to use a non-existent `.venv` virtual environment, but the project actually uses an `eshk` virtual environment. The error occurred because pip executables were corrupted.

**Original Error:**
```
Fatal error in launcher: Unable to create process using '"d:\trading_bot\multi_asset_bot\.venv\Scripts\python.exe"  "d:\trading_bot\multi_asset_bot\eshk\Scripts\pip.exe" install -r requirements.txt': The system cannot find the file specified.
```

**Solution Applied:**
- Fixed corrupted pip executables by reinstalling pip in the eshk environment
- Created helper batch files for easier environment usage
- Now `pip install -r requirements.txt` works correctly when eshk environment is activated

## Current Environment

- **Virtual Environment:** `eshk` (located in `d:\trading_bot\multi_asset_bot\eshk\`)
- **Python Version:** 3.10.0 (in virtual environment)
- **Global Python Version:** 3.13.7
- **Pip Version:** 25.2

## How to Use the Environment

### Method 1: Using Helper Batch Files (Recommended)

We've created several batch files to make working with the environment easier:

#### 1. Activate Environment
```cmd
activate_env.bat
```
This will:
- Activate the eshk virtual environment
- Show Python and pip versions
- Keep the command prompt open with the environment activated

#### 2. Install Packages
```cmd
pip_install.bat package_name
pip_install.bat -r requirements.txt
```
Examples:
- `pip_install.bat numpy`
- `pip_install.bat -r requirements.txt`

#### 3. Run Python Scripts
```cmd
run_python.bat script_name.py
run_python.bat main.py
run_python.bat test_integration.py --config config.yaml
```

### Method 2: Direct Commands

If you prefer to use direct commands:

#### Install packages:
```cmd
eshk\Scripts\python.exe -m pip install package_name
eshk\Scripts\python.exe -m pip install -r requirements.txt
```

#### Run Python scripts:
```cmd
eshk\Scripts\python.exe script_name.py
eshk\Scripts\python.exe main.py
```

#### Activate environment manually:
```cmd
eshk\Scripts\activate.bat
```

## Verification

To verify everything is working correctly:

1. **Check Python version:**
   ```cmd
   eshk\Scripts\python.exe --version
   ```
   Should output: `Python 3.10.0`

2. **Check pip version:**
   ```cmd
   eshk\Scripts\python.exe -m pip --version
   ```
   Should output: `pip 25.2 from d:\trading_bot\multi_asset_bot\eshk\lib\site-packages\pip (python 3.10)`

3. **Test package installation:**
   ```cmd
   eshk\Scripts\python.exe -m pip list
   ```
   Should show all installed packages including pandas, numpy, backtrader, etc.

## Installed Packages

All required packages from `requirements.txt` are already installed in the `eshk` environment, including:

- pandas, numpy, scipy
- backtrader, ccxt, oandapyV20, ibapi
- matplotlib, plotly
- scikit-learn, statsmodels
- TA-Lib, pandas-ta
- jupyter, ipython
- And many more...

## Troubleshooting

### If you get "The system cannot find the file specified" error:
- Make sure you're using the correct path: `eshk\Scripts\python.exe`
- Use the helper batch files provided
- Never use just `pip` or `python` - always specify the full path or use the batch files

### If packages seem missing:
- Verify you're using the eshk environment: `eshk\Scripts\python.exe -m pip list`
- Install missing packages: `eshk\Scripts\python.exe -m pip install package_name`

### If you want to create a new virtual environment:
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

## Notes

- The `eshk` directory contains a fully functional Python 3.10.0 virtual environment
- All project dependencies are already installed and working
- The helper batch files make it easy to work with this environment
- You can continue using this environment or create a new `.venv` if preferred