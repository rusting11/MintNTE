// auth_extractor.cpp — 管理员权限提取器 (Elevate.exe)
// 功能：若当前非管理员，自动触发 UAC 并重启自身；若已是管理员，则执行传入的命令行程序（权限传递给子进程）

#include <windows.h>
#include <shellapi.h>
#include <tchar.h>
#include <cstdio>

// 检查当前进程是否以管理员身份运行
BOOL IsRunAsAdmin() {
    BOOL isAdmin = FALSE;
    PSID adminGroup = NULL;
    SID_IDENTIFIER_AUTHORITY ntAuth = SECURITY_NT_AUTHORITY;
    if (AllocateAndInitializeSid(&ntAuth, 2,
        SECURITY_BUILTIN_DOMAIN_RID,
        DOMAIN_ALIAS_RID_ADMINS,
        0, 0, 0, 0, 0, 0, &adminGroup))
    {
        if (!CheckTokenMembership(NULL, adminGroup, &isAdmin))
            isAdmin = FALSE;
        FreeSid(adminGroup);
    }
    return isAdmin;
}

int _tmain(int argc, TCHAR* argv[]) {
    // 如果参数不足，显示用法
    if (argc < 2) {
        _tprintf(_T("用法: %s <程序路径> [参数...]\n"), argv[0]);
        _tprintf(_T("例如: %s python main.py\n"), argv[0]);
        return 1;
    }

    // 如果当前不是管理员，使用 runas 重新启动自身（触发 UAC）
    if (!IsRunAsAdmin()) {
        TCHAR exePath[MAX_PATH];
        GetModuleFileName(NULL, exePath, MAX_PATH);
        SHELLEXECUTEINFO sei = { sizeof(sei) };
        sei.lpVerb = _T("runas");
        sei.lpFile = exePath;
        sei.lpParameters = GetCommandLine();   // 原样传递命令行参数
        sei.nShow = SW_SHOWNORMAL;
        if (!ShellExecuteEx(&sei)) {
            DWORD err = GetLastError();
            if (err == ERROR_CANCELLED)
                _tprintf(_T("用户取消了 UAC。\n"));
            else
                _tprintf(_T("提权失败，错误码: %lu\n"), err);
            return 1;
        }
        return 0;   // 旧实例退出
    }

    // 此时已经以管理员身份运行，启动目标程序
    // 将参数拼接为一个命令行字符串
    TCHAR cmdLine[32768] = { 0 };
    for (int i = 1; i < argc; i++) {
        _tcscat_s(cmdLine, argv[i]);
        _tcscat_s(cmdLine, _T(" "));
    }

    STARTUPINFO si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    if (!CreateProcess(NULL, cmdLine, NULL, NULL, FALSE,
        CREATE_DEFAULT_ERROR_MODE | CREATE_NEW_CONSOLE, NULL, NULL, &si, &pi)) {
        _tprintf(_T("启动目标程序失败: %s (错误 %lu)\n"), cmdLine, GetLastError());
        return 1;
    }

    // 等待目标程序运行结束（可选）
    WaitForSingleObject(pi.hProcess, INFINITE);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return 0;
}