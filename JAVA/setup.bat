@echo off
REM Setup script for Java TAC Optimizer project
REM This script installs all necessary dependencies

echo ============================================
echo  JAVA TAC OPTIMIZER - SETUP
echo ============================================
echo.

REM Check if Java is installed
echo [1/4] Checking Java installation...
java -version 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Java is not installed or not in PATH!
    echo Please install Java JDK 8 or higher from: https://www.oracle.com/java/technologies/downloads/
    pause
    exit /b 1
)
echo [OK] Java is installed
echo.

REM Check if Python is installed
echo [2/4] Checking Python installation...
python --version 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.7+ from: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python is installed
echo.

REM Download Soot framework
echo [3/4] Setting up Soot framework...
if not exist lib mkdir lib
cd lib

if not exist soot-4.5.0-jar-with-dependencies.jar (
    echo Downloading Soot JAR file...
    echo Please download Soot manually from:
    echo https://repo1.maven.org/maven2/org/soot-oss/soot/4.5.0/soot-4.5.0-jar-with-dependencies.jar
    echo.
    echo Save it to: %CD%
    echo.
    echo Alternative: Use this PowerShell command to download:
    echo powershell -Command "Invoke-WebRequest -Uri 'https://repo1.maven.org/maven2/org/soot-oss/soot/4.5.0/soot-4.5.0-jar-with-dependencies.jar' -OutFile 'soot-4.5.0-jar-with-dependencies.jar'"
    echo.
    
    REM Try to download using PowerShell
    powershell -Command "Invoke-WebRequest -Uri 'https://repo1.maven.org/maven2/org/soot-oss/soot/4.5.0/soot-4.5.0-jar-with-dependencies.jar' -OutFile 'soot-4.5.0-jar-with-dependencies.jar'" 2>nul
    
    if exist soot-4.5.0-jar-with-dependencies.jar (
        echo [OK] Soot downloaded successfully
    ) else (
        echo [WARNING] Could not auto-download Soot. Please download manually.
        echo The project will still work if you download Soot later.
    )
) else (
    echo [OK] Soot JAR already exists
)

cd ..
echo.

REM Create output directories
echo [4/4] Creating output directories...
if not exist jimple_output mkdir jimple_output
if not exist jimple_output\optimized mkdir jimple_output\optimized
echo [OK] Directories created
echo.

echo ============================================
echo  SETUP COMPLETE!
echo ============================================
echo.
echo Next steps:
echo   1. Run: compile.bat     (Compile Java programs)
echo   2. Run: generate_tac.bat (Generate Jimple TAC)
echo   3. Run: optimize.bat     (Run optimizer)
echo.
echo Or simply run: run_all.bat (Does all steps)
echo.
pause
