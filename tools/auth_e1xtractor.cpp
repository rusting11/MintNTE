// Elevate.cpp - 自动获取管理员权限
// 编译: cl /EHsc Elevate.cpp /link shell32.lib advapi32.lib
// 使用: 如果当前不是管理员，则自动提权重启自身

#include <windows.h>
#include <shellapi.h>
#include <tchar.h>
#include <stdio.h>

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

BOOL ElevateSelf() {
    TCHAR exePath[MAX_PATH];
    if (GetModuleFileName(NULL, exePath, MAX_PATH) == 0)
        return FALSE;

    // 获取原命令行
    LPTSTR cmdLine = GetCommandLine();

    // 使用 ShellExecuteEx 以 runas 重新启动
    SHELLEXECUTEINFO sei = { sizeof(sei) };
    sei.lpVerb = _T("runas");
    sei.lpFile = exePath;
    sei.lpParameters = cmdLine;   // 保留原参数
    sei.hwnd = NULL;
    sei.nShow = SW_SHOWNORMAL;

    if (!ShellExecuteEx(&sei)) {
        DWORD err = GetLastError();
        if (err == ERROR_CANCELLED)
            _tprintf(_T("用户取消了 UAC 提权。\n"));
        else
            _tprintf(_T("提权失败，错误码: %lu\n"), err);
        return FALSE;
    }
    return TRUE;
}

int _tmain(int argc, TCHAR* argv[]) {
    if (!IsRunAsAdmin()) {
        _tprintf(_T("当前未以管理员身份运行，正在请求提权...\n"));
        if (ElevateSelf()) {
            // 提权成功，新进程已启动，当前进程退出
            return 0;
        } else {
            _tprintf(_T("提权失败，继续以普通权限运行。\n"));
            // 如果提权失败，仍然可以继续运行
        }
    } else {
        _tprintf(_T("已经以管理员身份运行。\n"));
    }

    // 这里放入你的需要管理员权限的代码
    // 例如：等待用户按键后退出
    _tprintf(_T("按任意键退出...\n"));
    _getch();
    return 0;
}