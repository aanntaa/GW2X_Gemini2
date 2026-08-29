#pragma once

#include "../Core/Architecture/IFeature.h"
#include "../Input/InputManager.h"

namespace kx::Features {

    /**
     * @brief Example feature demonstrating input system usage.
     * 
     * This feature showcases:
     * - Keyboard input handling
     * - Mouse input handling
     * - Gamepad input handling
     * - Input-based feature control
     */
    class InputTestFeature : public IFeature {
    public:
        InputTestFeature() = default;
        ~InputTestFeature() override = default;

        bool Initialize(const ServiceContext& ctx) override;
        void Shutdown() override;
        void Update(float deltaTime, const FrameGameData& frameData, const ServiceContext& ctx) override;
        void RenderDrawList(ImDrawList* drawList, const ServiceContext& ctx) override;
        void OnMenuRender() override;
        bool OnInput(UINT message, WPARAM wParam, LPARAM lParam) override;
        const char* GetName() const override { return "InputTestFeature"; }
        void LoadSettings(const nlohmann::json& j) override;
        void SaveSettings(nlohmann::json& j) override;

    private:
        bool m_enabled = true;
        bool m_showDebugInfo = true;
        
        // Input state tracking
        struct InputDebugInfo {
            int lastKeyDown = -1;
            float mouseX = 0.0f, mouseY = 0.0f;
            int gamepadButtons = 0;
            float gamepadStickX = 0.0f, gamepadStickY = 0.0f;
        } m_debugInfo;
    };

} // namespace kx::Features
