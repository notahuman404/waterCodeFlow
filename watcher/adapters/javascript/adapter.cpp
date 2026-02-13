#include <watcher_core.hpp>
#include <node_api.h>
#include <node.h>
#include <iostream>
#include <memory>

// ============================================================================
// N-API Bindings for JavaScript
// ============================================================================

// Wrapper for WatcherCore singleton
static watcher::WatcherCore* g_core = nullptr;

napi_value Initialize(napi_env env, napi_callback_info info) {
    napi_status status;
    size_t argc = 1;
    napi_value argv[1];
    
    status = napi_get_cb_info(env, info, &argc, argv, nullptr, nullptr);
    if (status != napi_ok) {
        napi_throw_error(env, nullptr, "Failed to get callback info");
        return nullptr;
    }
    
    size_t output_dir_len = 0;
    char output_dir[256];
    
    status = napi_get_value_string_utf8(env, argv[0], output_dir, sizeof(output_dir), &output_dir_len);
    if (status != napi_ok) {
        napi_throw_error(env, nullptr, "Failed to get output directory");
        return nullptr;
    }
    
    g_core = &watcher::WatcherCore::getInstance();
    if (!g_core->initialize(std::string(output_dir, output_dir_len))) {
        napi_throw_error(env, nullptr, "Failed to initialize watcher core");
        return nullptr;
    }
    
    napi_value result;
    napi_get_boolean(env, true, &result);
    return result;
}

napi_value Start(napi_env env, napi_callback_info info) {
    if (!g_core) {
        napi_throw_error(env, nullptr, "Watcher core not initialized");
        return nullptr;
    }
    
    bool success = g_core->start();
    napi_value result;
    napi_get_boolean(env, success, &result);
    return result;
}

napi_value Stop(napi_env env, napi_callback_info info) {
    if (!g_core) {
        napi_throw_error(env, nullptr, "Watcher core not initialized");
        return nullptr;
    }
    
    bool success = g_core->stop();
    napi_value result;
    napi_get_boolean(env, success, &result);
    return result;
}

napi_value RegisterPage(napi_env env, napi_callback_info info) {
    if (!g_core) {
        napi_throw_error(env, nullptr, "Watcher core not initialized");
        return nullptr;
    }
    
    size_t argc = 4;
    napi_value argv[4];
    napi_get_cb_info(env, info, &argc, argv, nullptr, nullptr);
    
    // Get page base address
    void* page_base;
    napi_get_buffer_info(env, argv[0], &page_base, nullptr);
    
    // Get page size
    uint32_t page_size;
    napi_get_value_uint32(env, argv[1], &page_size);
    
    // Get variable name
    size_t name_len = 0;
    char name[256];
    napi_get_value_string_utf8(env, argv[2], name, sizeof(name), &name_len);
    
    // Get flags
    uint32_t flags;
    napi_get_value_uint32(env, argv[3], &flags);
    
    watcher::MutationDepth depth{true, 0};
    std::string var_id = g_core->registerPage(
        page_base, page_size, std::string(name, name_len),
        static_cast<watcher::EventFlags>(flags), depth
    );
    
    napi_value result;
    napi_create_string_utf8(env, var_id.c_str(), var_id.length(), &result);
    return result;
}

napi_value UnregisterPage(napi_env env, napi_callback_info info) {
    if (!g_core) {
        napi_throw_error(env, nullptr, "Watcher core not initialized");
        return nullptr;
    }
    
    size_t argc = 1;
    napi_value argv[1];
    napi_get_cb_info(env, info, &argc, argv, nullptr, nullptr);
    
    size_t var_id_len = 0;
    char var_id[256];
    napi_get_value_string_utf8(env, argv[0], var_id, sizeof(var_id), &var_id_len);
    
    bool success = g_core->unregisterPage(std::string(var_id, var_id_len));
    
    napi_value result;
    napi_get_boolean(env, success, &result);
    return result;
}

napi_value GetState(napi_env env, napi_callback_info info) {
    if (!g_core) {
        napi_throw_error(env, nullptr, "Watcher core not initialized");
        return nullptr;
    }
    
    napi_value result;
    napi_create_uint32(env, static_cast<uint32_t>(g_core->getState()), &result);
    return result;
}

#define DECLARE_NAPI_METHOD(name, func) \
  { name, 0, func, 0, 0, 0, napi_default, 0 }

static napi_value Init(napi_env env, napi_value exports) {
    napi_status status;
    napi_property_descriptor properties[] = {
        DECLARE_NAPI_METHOD("initialize", Initialize),
        DECLARE_NAPI_METHOD("start", Start),
        DECLARE_NAPI_METHOD("stop", Stop),
        DECLARE_NAPI_METHOD("registerPage", RegisterPage),
        DECLARE_NAPI_METHOD("unregisterPage", UnregisterPage),
        DECLARE_NAPI_METHOD("getState", GetState),
    };
    
    status = napi_define_properties(
        env, exports, sizeof(properties) / sizeof(properties[0]), properties);
    
    if (status != napi_ok) {
        napi_throw_error(env, nullptr, "Failed to define properties");
    }
    
    return exports;
}

NAPI_MODULE(watcher_core, Init)
