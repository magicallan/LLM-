@echo off
conda env list
call activate py39_torch_gpu
D:
cd D:\PythonProject\LLM部署
python QA_pre.py
pause & exit