# Restart UI Mechanism

## Overview

The "Restart UI" button in the Settings panel allows users to quickly restart the HappyMeasure application without manually closing and reopening it.

## Current Implementation

### Development Mode (Running from Python)
When running from `python src/keith_ivt/ui/simple_app.py` or similar:
- Restarts the Python interpreter with the same script
- Uses `subprocess.Popen()` with detached process flags
- Works correctly in development environments

### Production Mode (Running from .bat/.exe)
When running from `Run_HappyMeasure.bat` or a compiled executable:
- Should restart the launcher process (.bat or .exe)
- Currently detects `.py` extension to determine mode
- **Note**: May need refinement for final release packaging

## Technical Details

### Process Detachment (Windows)
```python
subprocess.Popen(
    args,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    close_fds=True
)
```

This ensures the new process is independent of the old one, allowing the old process to terminate cleanly.

### Known Limitations

1. **Batch File Detection**: The current implementation checks if `sys.argv[0]` ends with `.py`. For production releases packaged as `.exe`, this logic may need adjustment.

2. **Environment Variables**: The restarted process inherits the current environment. If the launcher sets specific environment variables, they should be preserved.

3. **Working Directory**: The restart maintains the current working directory. Ensure this is correct for your deployment.

## Future Improvements for Release

### Option 1: Launcher Detection
Detect the actual launcher by checking parent process:
```python
import psutil
parent = psutil.Process(os.getpid()).parent()
launcher = parent.cmdline()[0] if parent else None
```

### Option 2: Restart Marker File
Create a temporary marker file that the launcher checks on startup:
```python
# On restart request
Path("restart.marker").write_text("1")
# In Run_HappyMeasure.bat
if exist restart.marker del restart.marker && goto start
```

### Option 3: Separate Restart Helper
Create a small helper executable that:
1. Waits for the main process to exit
2. Restarts the main application
3. Cleans up temporary files

## Testing

To test the restart functionality:

1. **Development mode**:
   ```bash
   python src/keith_ivt/ui/simple_app.py
   # Click Settings → Restart UI
   ```

2. **Batch mode**:
   ```bash
   Run_HappyMeasure.bat
   # Click Settings → Restart UI
   ```

## Related Files

- `src/keith_ivt/ui/panels.py` - Contains `_restart_ui()` method
- `Run_HappyMeasure.bat` - Windows batch launcher
- `Run_HappyMeasure.ps1` - PowerShell launcher alternative
