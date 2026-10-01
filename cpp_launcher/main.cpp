#include <windows.h>
#include <shellapi.h>

#include <cstdio>
#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

namespace {

struct PythonCommand {
    std::wstring executable;
    std::wstring prefix;
};

bool showConsole = false;

void reportError(const std::wstring& message) {
    if (showConsole) {
        std::wcerr << message << L'\n';
    }
    MessageBoxW(nullptr, message.c_str(), L"CoD2 MP Mapping Tool",
                MB_OK | MB_ICONERROR);
}

bool hasConsoleFlag() {
    int argumentCount = 0;
    LPWSTR* arguments = CommandLineToArgvW(GetCommandLineW(), &argumentCount);
    if (arguments == nullptr) {
        return false;
    }

    bool enabled = false;
    for (int index = 1; index < argumentCount; ++index) {
        if (arguments[index] == std::wstring(L"--console")) {
            enabled = true;
            break;
        }
    }
    LocalFree(arguments);
    return enabled;
}

void enableConsole() {
    if (!AllocConsole()) {
        showConsole = false;
        return;
    }

    FILE* stream = nullptr;
    freopen_s(&stream, "CONIN$", "r", stdin);
    freopen_s(&stream, "CONOUT$", "w", stdout);
    freopen_s(&stream, "CONOUT$", "w", stderr);
}

std::wstring quoteArgument(const std::wstring& argument) {
    std::wstring quoted = L"\"";
    for (wchar_t character : argument) {
        if (character == L'"') {
            quoted += L'\\';
        }
        quoted += character;
    }
    quoted += L'"';
    return quoted;
}

std::wstring resolveExecutable(const std::wstring& executable) {
    std::vector<wchar_t> searchPath(32768);
    const DWORD pathLength = GetEnvironmentVariableW(
        L"PATH", searchPath.data(), static_cast<DWORD>(searchPath.size()));
    if (pathLength == 0 || pathLength >= searchPath.size()) {
        return {};
    }

    std::vector<wchar_t> resolvedPath(32768);
    const DWORD length = SearchPathW(
        searchPath.data(), executable.c_str(), L".exe",
        static_cast<DWORD>(resolvedPath.size()), resolvedPath.data(), nullptr);
    if (length == 0 || length >= resolvedPath.size()) {
        return {};
    }
    return resolvedPath.data();
}

bool runProcess(const PythonCommand& python, const std::wstring& arguments,
                DWORD& exitCode,
                const std::filesystem::path* workingDirectory = nullptr) {
    const std::wstring executablePath = resolveExecutable(python.executable);
    if (executablePath.empty()) {
        return false;
    }

    std::wstring commandLine = quoteArgument(executablePath);
    if (!python.prefix.empty()) {
        commandLine += L" " + python.prefix;
    }
    if (!arguments.empty()) {
        commandLine += L" " + arguments;
    }

    STARTUPINFOW startupInfo{};
    startupInfo.cb = sizeof(startupInfo);
    PROCESS_INFORMATION processInfo{};
    const DWORD creationFlags = showConsole ? 0 : CREATE_NO_WINDOW;

    if (!CreateProcessW(executablePath.c_str(), commandLine.data(), nullptr,
                        nullptr, TRUE, creationFlags, nullptr,
                        workingDirectory ? workingDirectory->c_str() : nullptr,
                        &startupInfo, &processInfo)) {
        return false;
    }

    CloseHandle(processInfo.hThread);
    WaitForSingleObject(processInfo.hProcess, INFINITE);
    const BOOL gotExitCode = GetExitCodeProcess(processInfo.hProcess, &exitCode);
    CloseHandle(processInfo.hProcess);
    return gotExitCode != FALSE;
}

bool canRunPython(const PythonCommand& python) {
    DWORD exitCode = 1;
    return runProcess(python, L"--version", exitCode) && exitCode == 0;
}

bool dependenciesAvailable(const PythonCommand& python) {
    DWORD exitCode = 1;
    return runProcess(python, L"-c \"import PyQt6, psutil\"", exitCode) &&
           exitCode == 0;
}

std::filesystem::path findProjectRoot() {
    std::vector<wchar_t> executablePath(32768);
    const DWORD length = GetModuleFileNameW(
        nullptr, executablePath.data(), static_cast<DWORD>(executablePath.size()));
    if (length == 0 || length >= executablePath.size()) {
        return {};
    }

    std::filesystem::path directory =
        std::filesystem::path(executablePath.data()).parent_path();
    for (int depth = 0; depth < 8 && !directory.empty(); ++depth) {
        if (std::filesystem::exists(directory / L"main.py")) {
            return directory;
        }
        const auto parent = directory.parent_path();
        if (parent == directory) {
            break;
        }
        directory = parent;
    }
    return {};
}

}  // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    showConsole = hasConsoleFlag();
    if (showConsole) {
        enableConsole();
    }

    const std::filesystem::path projectRoot = findProjectRoot();
    if (projectRoot.empty()) {
        reportError(L"Could not find main.py next to the launcher or in a parent folder.");
        return 1;
    }

    const std::filesystem::path mainScript = projectRoot / L"main.py";
    const std::vector<PythonCommand> candidates = {
        {L"python3.exe", L""},
        {L"python.exe", L""},
        {L"py.exe", L"-3"},
    };

    PythonCommand python;
    bool foundPython = false;
    for (const auto& candidate : candidates) {
        if (canRunPython(candidate)) {
            python = candidate;
            foundPython = true;
            break;
        }
    }

    if (!foundPython) {
        reportError(L"Python 3 was not found. Install it from https://www.python.org/downloads/ "
                    L"and make sure python3.exe, python.exe, or the Python Launcher is available on PATH.");
        return 1;
    }

    if (!dependenciesAvailable(python)) {
        const int installChoice = MessageBoxW(
            nullptr,
            L"PyQt6 and/or psutil are missing. Install the required packages now with pip?",
            L"Missing dependencies",
            MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2);
        if (installChoice != IDYES) {
            return 1;
        }

        if (!showConsole) {
            MessageBoxW(nullptr,
                        L"Installing PyQt6 and psutil. This may take several minutes.",
                        L"Installing dependencies", MB_OK | MB_ICONINFORMATION);
        } else {
            std::wcout << L"Installing PyQt6 and psutil...\n";
        }
        DWORD installExitCode = 1;
        if (!runProcess(python, L"-m pip install PyQt6 psutil", installExitCode) ||
            installExitCode != 0) {
            reportError(L"Package installation failed. Check that pip is available. "
                        L"Run the launcher with --console for diagnostic output.");
            return 1;
        }

        if (!dependenciesAvailable(python)) {
            reportError(L"The required packages are still unavailable after installation.");
            return 1;
        }
    }

    if (showConsole) {
        std::wcout << L"Starting the mapping tool...\n";
    }
    DWORD applicationExitCode = 1;
    const std::wstring scriptArgument = quoteArgument(mainScript.wstring());
    if (!runProcess(python, scriptArgument, applicationExitCode,
                    &projectRoot)) {
        reportError(L"Could not start Python. Check its installation and PATH.");
        return 1;
    }
    if (applicationExitCode != 0) {
        reportError(L"The application exited with code " +
                    std::to_wstring(applicationExitCode) +
                    L". Run the launcher with --console for diagnostic output.");
    }
    return static_cast<int>(applicationExitCode);
}