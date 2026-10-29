/* Experimental US v304 Aroma companion. No Nintendo code is bundled. */
#include <wups.h>
#undef DECL_FUNCTION
#include <function_patcher/function_patching.h>
#include <coreinit/debug.h>
#include <coreinit/dynload.h>
#include <coreinit/title.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

WUPS_PLUGIN_NAME("Hidden CSS Giga Respawn (experimental)");
WUPS_PLUGIN_DESCRIPTION("US v304 only: preserve directly selected Giga Bowser after KO");
WUPS_PLUGIN_VERSION("0.1.0-experimental");
WUPS_PLUGIN_AUTHOR("CSS Expansion Contributors");
WUPS_PLUGIN_LICENSE("MIT");

#define ENTRY_INIT_ADDRESS 0x02E45558u
#define GIGA_ASSIGNMENT_ADDRESS 0x02E45708u
#define US_TITLE_ID UINT64_C(0x0005000010144F00)

static uint32_t (*real_initialize_entry)(void *);
static PatchedFunctionHandle patch_handle;
static bool library_ready;
static volatile bool hook_enabled;
static const uint64_t allowed_titles[] = {US_TITLE_ID};

static uint32_t my_initialize_entry(void *entry) {
    /* Preserve the native r3 return even if callers treat this routine as void. */
    uint32_t result = real_initialize_entry(entry);
    if (hook_enabled && entry != NULL) {
        volatile uint32_t *kind = (volatile uint32_t *)((uint8_t *)entry + 0x10);
        volatile uint32_t *alternate = (volatile uint32_t *)((uint8_t *)entry + 0x14);
        if (*kind == 58u && *alternate == 15u) {
            *alternate = 58u;
        }
    }
    return result;
}

static bool code_matches(void) {
    const volatile uint32_t *start = (const volatile uint32_t *)ENTRY_INIT_ADDRESS;
    const volatile uint32_t *assignment = (const volatile uint32_t *)GIGA_ASSIGNMENT_ADDRESS;
    return start[0] == 0x7C0802A6u && start[1] == 0x9421FFF0u &&
           start[2] == 0x93E1000Cu && start[3] == 0x7C7F1B78u &&
           assignment[0] == 0x398000CCu && assignment[1] == 0x3800000Fu &&
           assignment[2] == 0x999F14EEu && assignment[3] == 0x901F0014u;
}

static bool find_executable(uint32_t *text_offset, const char **name) {
    int count = OSDynLoad_GetNumberOfRPLs();
    if (count <= 0 || count > 256) return false;
    for (int i = 0; i < count; ++i) {
        OSDynLoad_NotifyData module;
        if (!OSDynLoad_GetRPLInfo((uint32_t)i, 1, &module) || module.name == NULL) continue;
        const char *base = strrchr(module.name, '/');
        base = base ? base + 1 : module.name;
        if (strcmp(base, "cross_f.rpx") != 0 && strcmp(base, "cross_f") != 0) continue;
        if (ENTRY_INIT_ADDRESS < module.textAddr || GIGA_ASSIGNMENT_ADDRESS < module.textAddr) return false;
        uint32_t init_offset = ENTRY_INIT_ADDRESS - module.textAddr;
        uint32_t guard_offset = GIGA_ASSIGNMENT_ADDRESS - module.textAddr;
        if (module.textSize < 16 || init_offset > module.textSize - 16 || guard_offset > module.textSize - 16) return false;
        *text_offset = init_offset;
        *name = strcmp(base, "cross_f.rpx") == 0 ? "cross_f.rpx" : "cross_f";
        return true;
    }
    return false;
}

static void stop_hook(void) {
    hook_enabled = false;
    if (patch_handle != 0 && library_ready) {
        FunctionPatcherStatus status = FunctionPatcher_RemoveFunctionPatch(patch_handle);
        if (status != FUNCTION_PATCHER_RESULT_SUCCESS) {
            OSReport("[HiddenCSS] Hook removal failed: %s\n", FunctionPatcher_GetStatusStr(status));
            return;
        }
        patch_handle = 0;
    }
    if (library_ready) {
        FunctionPatcher_DeInitLibrary();
        library_ready = false;
    }
}

ON_APPLICATION_START() {
    stop_hook();
    if (patch_handle != 0 || OSGetTitleID() != US_TITLE_ID) return;
    uint32_t offset;
    const char *name;
    /* Establish mapped text bounds before reading any fixed-address signature. */
    if (!find_executable(&offset, &name) || !code_matches()) return;
    if (FunctionPatcher_InitLibrary() != FUNCTION_PATCHER_RESULT_SUCCESS) return;
    library_ready = true;
    function_replacement_data_t replacement =
        REPLACE_FUNCTION_OF_EXECUTABLE_BY_ADDRESS_WITH_VERSION(initialize_entry,
            allowed_titles, 1, name, offset, 304, 304);
    bool applied = false;
    FunctionPatcherStatus status = FunctionPatcher_AddFunctionPatch(&replacement, &patch_handle, &applied);
    if (status != FUNCTION_PATCHER_RESULT_SUCCESS || !applied) {
        OSReport("[HiddenCSS] US v304 respawn hook was not applied.\n");
        stop_hook();
        return;
    }
    hook_enabled = true;
    OSReport("[HiddenCSS] Experimental Giga respawn hook active for US v304.\n");
}

ON_APPLICATION_ENDS() { stop_hook(); }
DEINITIALIZE_PLUGIN() { stop_hook(); }
