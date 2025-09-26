@echo off
setlocal EnableDelayedExpansion

echo Testing system status function...

:show_system_status
echo [Runtime Status]
if exist ".venv\Scripts\python.exe" (
    echo Found Python executable
    .\.venv\Scripts\python.exe -c "try: import torch; cuda_available = torch.cuda.is_available(); gpu_name = torch.cuda.get_device_name(0) if cuda_available else 'N/A'; pytorch_version = torch.__version__; print(f'Runtime: PyTorch {pytorch_version} | GPU: {gpu_name}') if cuda_available else print(f'Runtime: PyTorch {pytorch_version} | CPU-Only Mode'); except Exception: print('Runtime: Python | Status: Checking...')" 2>nul
) else (
    echo Runtime: Python | Status: Not installed
)
echo.
goto :eof

call :show_system_status
echo Status check completed.
pause