@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 设置颜色变量
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
    set "DEL=%%a"
)
set "Green=%DEL%[32m"
set "Red=%DEL%[31m"
set "Default=%DEL%[0m"
set "Yellow=%DEL%[33m"

:: 获取当前年份
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set datetime=%%a
set year=%datetime:~0,4%

:: 版权信息
echo =============================================
echo Nian Yi_Aggregation Environment Dependency Installation Script
echo Copyright (c) %year% Nian Yi. All rights reserved.
echo 本作品采用知识共享署名4.0国际许可协议进行许可。
echo This work is licensed under the Creative Commons Attribution 4.0 International License.
echo =============================================
echo.

:: 检查Python是否安装
echo %Yellow%正在检查 Python 安装状态...%Default%
python -V >nul 2>&1
if %errorlevel% neq 0 (
    echo %Red%Python未安装，请先安装Python！%Default%
    pause
    exit /b
)

:: 初始化计数器
set total_count=0
set success_count=0
set fail_count=0

:: 读取依赖列表文件
set "dependency_file=..\config\DependenciesList.txt"
if not exist "%dependency_file%" (
    echo %Red%依赖列表文件 %dependency_file% 不存在！%Default%
    pause
    exit /b
)

:: 显示文件内容
echo %Yellow%将安装以下依赖项：%Default%
type "%dependency_file%"
echo.

:: 遍历依赖列表并安装
for /f "tokens=*" %%d in ('type "%dependency_file%" ^| findstr /r /v "^[[:space:]]*$"') do (
    set "package=%%d"
    set "package=!package: =!"
    set "package=!package:    =!"
    
    if not "!package!"=="" (
        set /a total_count+=1
        echo ============================================
        echo 正在安装 !package!...
        echo ============================================
        
        pip install !package!
        if !errorlevel! equ 0 (
            echo %Green%!package! 安装成功%Default%
            set "status_!package!=成功"
            set /a success_count+=1
        ) else (
            echo %Red%!package! 安装失败%Default%
            set "status_!package!=失败"
            set /a fail_count+=1
        )
        echo.
    )
)

:: 显示详细安装结果
echo.
echo ============================================
echo %Yellow%安装详细结果：%Default%
echo ============================================

for /f "tokens=*" %%d in ('type "%dependency_file%" ^| findstr /r /v "^[[:space:]]*$"') do (
    set "package=%%d"
    set "package=!package: =!"
    set "package=!package:    =!"
    
    if not "!package!"=="" (
        for /f "tokens=2 delims==" %%s in ('set status_!package! 2^>nul') do (
            if "%%s"=="成功" (
                echo %Green%!package! - 成功%Default%
            ) else (
                echo %Red%!package! - 失败%Default%
            )
        )
    )
)

:: 输出统计结果
echo.
echo ============================================
echo %Yellow%安装统计：%Default%
echo ============================================
echo 总计: %total_count%
echo %Green%成功: %success_count%%Default%
echo %Red%失败: %fail_count%%Default%
echo ============================================
echo.

:: 保持窗口打开
pause