@echo off
REM Compile all Java source files

echo ============================================
echo  COMPILING JAVA PROGRAMS
echo ============================================
echo.

REM Check if Soot JAR exists
if not exist lib\soot-4.5.0-jar-with-dependencies.jar (
    echo [ERROR] Soot JAR not found in lib directory
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Compile test programs
echo [1/4] Compiling TestProgram1.java...
javac TestProgram1.java
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to compile TestProgram1.java
    pause
    exit /b 1
)
echo [OK] TestProgram1 compiled

echo [2/4] Compiling TestProgram2.java...
javac TestProgram2.java
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to compile TestProgram2.java
    pause
    exit /b 1
)
echo [OK] TestProgram2 compiled

echo [3/4] Compiling TestProgram3.java...
javac TestProgram3.java
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to compile TestProgram3.java
    pause
    exit /b 1
)
echo [OK] TestProgram3 compiled

echo [4/4] Compiling JimpleGenerator.java...
javac -cp ".;lib\soot-4.5.0-jar-with-dependencies.jar" JimpleGenerator.java
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to compile JimpleGenerator.java
    pause
    exit /b 1
)
echo [OK] JimpleGenerator compiled

echo.
echo ============================================
echo  COMPILATION COMPLETE!
echo ============================================
echo.
echo All Java files compiled successfully.
echo Next step: Run generate_tac.bat to generate Jimple TAC
echo.
pause
