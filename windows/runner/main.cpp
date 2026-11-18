#include <flutter/dart_project.h>
#include <flutter/flutter_view_controller.h>
#include <windows.h>

#include "flutter_window.h"
#include "utils.h"

int APIENTRY wWinMain(_In_ HINSTANCE instance, _In_opt_ HINSTANCE prev,
                      _In_ wchar_t *command_line, _In_ int show_command) {
  // Attach to console when present (e.g., 'flutter run') or create a
  // new console when running with a debugger.
  if (!::AttachConsole(ATTACH_PARENT_PROCESS) && ::IsDebuggerPresent()) {
    CreateAndAttachConsole();
  }

  // Initialize COM, so that it is available for use in the library and/or
  // plugins.
  ::CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);

  flutter::DartProject project(L"data");

  std::vector<std::string> command_line_arguments =
      GetCommandLineArguments();

  project.set_dart_entrypoint_arguments(std::move(command_line_arguments));

  FlutterWindow window(project);
  // window title, as code points so the source stays plain ASCII
  const wchar_t title[] = {0x0633, 0x06CC, 0x0633, 0x062A, 0x06D5, 0x0645, 0x06CC, 0x0020, 0x062D, 0x06CC, 0x0633, 0x0627, 0x0628, 0x0627, 0x062A, 0x06CC, 0x0020, 0x062F, 0x0648, 0x0648, 0x06A9, 0x0627, 0x0646, 0x06CC, 0x0020, 0x062C, 0x0648, 0x0645, 0x0644, 0x06D5, 0};
  Win32Window::Point origin(40, 30);
  Win32Window::Size size(1400, 880);
  if (!window.Create(title, origin, size)) {
    return EXIT_FAILURE;
  }
  window.SetQuitOnClose(true);

  ::MSG msg;
  while (::GetMessage(&msg, nullptr, 0, 0)) {
    ::TranslateMessage(&msg);
    ::DispatchMessage(&msg);
  }

  ::CoUninitialize();
  return EXIT_SUCCESS;
}
