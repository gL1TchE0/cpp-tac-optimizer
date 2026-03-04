@echo off
REM Run complete pipeline: Compile -> Generate TAC -> Optimize

echo ============================================
echo  JAVA TAC OPTIMIZER - COMPLETE PIPELINE
echo ============================================
echo.

REM Step 1: Setup
echo STEP 1: SETUP
echo --------------------------------------------
if not exist lib\soot-4.5.0-jar-with-dependencies.jar (
    echo Running setup...
    call setup.bat
    if %ERRORLEVEL% NEQ 0 exit /b 1
) else (
    echo Setup already complete, skipping...
    echo.
)

REM Step 2: Compile
echo.
echo STEP 2: COMPILATION
echo --------------------------------------------
call compile.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Compilation failed
    pause
    exit /b 1
)

REM Step 3: Generate TAC
echo.
echo STEP 3: TAC GENERATION
echo --------------------------------------------
call generate_tac.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] TAC generation failed
    pause
    exit /b 1
)

REM Step 4: Optimize
echo.
echo STEP 4: OPTIMIZATION
echo --------------------------------------------
call optimize.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Optimization failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo  COMPLETE PIPELINE FINISHED!
echo ============================================
echo.
echo Results:
echo   - Original Java files:     TestProgram*.java
echo   - Compiled classes:        TestProgram*.class
echo   - Original TAC (Jimple):   jimple_output\*.jimple
echo   - Optimized TAC (Jimple):  jimple_output\optimized\*.optimized.jimple
echo.
echo Check the optimized\ directory to see the improvements!
echo.
pause
