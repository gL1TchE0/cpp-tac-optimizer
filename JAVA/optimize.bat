@echo off
REM Run TAC optimizer on generated Jimple files

echo ============================================
echo  OPTIMIZING JIMPLE TAC
echo ============================================
echo.

REM Check if Jimple files exist
if not exist jimple_output\*.jimple (
    echo [ERROR] Jimple files not found. Please run generate_tac.bat first
    pause
    exit /b 1
)

echo Running comprehensive TAC optimizer...
echo.
echo Optimizations applied:
echo   - Constant Propagation
echo   - Constant Folding
echo   - Algebraic Simplification
echo   - Strength Reduction
echo   - Copy Propagation
echo   - Common Subexpression Elimination
echo   - Dead Code Elimination
echo   - Unreachable Code Elimination
echo   - Loop Optimization
echo.
echo ============================================
echo.

python jimple_optimizer.py jimple_output

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Optimizer failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo  OPTIMIZATION COMPLETE!
echo ============================================
echo.
echo Original TAC files:   jimple_output\*.jimple
echo Optimized TAC files:  jimple_output\optimized\*.optimized.jimple
echo.
echo You can compare the files to see the optimizations applied!
echo.
pause
