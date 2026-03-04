@echo off
REM Generate Jimple TAC from compiled Java classes

echo ============================================
echo  GENERATING JIMPLE TAC
echo ============================================
echo.

REM Check if classes are compiled
if not exist TestProgram1.class (
    echo [ERROR] Class files not found. Please run compile.bat first
    pause
    exit /b 1
)

REM Clean previous output
if exist jimple_output (
    echo Cleaning previous output...
    del /Q jimple_output\*.jimple 2>nul
)

echo Generating Jimple (Three-Address Code) from Java bytecode...
echo.

java -cp ".;lib\soot-4.5.0-jar-with-dependencies.jar" JimpleGenerator TestProgram1 TestProgram2 TestProgram3

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to generate Jimple TAC
    pause
    exit /b 1
)

echo.
echo ============================================
echo  JIMPLE TAC GENERATION COMPLETE!
echo ============================================
echo.
echo Jimple files generated in: jimple_output\
echo Next step: Run optimize.bat to optimize the TAC
echo.
pause
