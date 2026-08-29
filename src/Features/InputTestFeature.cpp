#include "InputTestFeature.h"
#include "../Core/Architecture/ServiceContext.h"
#include "../Utils/DebugLogger.h"
#include "../../libs/ImGui/imgui.h"
#include <winuser.h>

namespace kx::Features {

    bool InputTestFeature::Initialize(const ServiceContext& ctx) {
        LOG_INFO("[InputTestFeature] Initialized");
        return true;
    }

    void InputTestFeature::Shutdown() {
        LOG_INFO("[InputTestFeature] Shutdown");
    }

    void InputTestFeature::Update(float deltaTime, const FrameGameData& frameData, const ServiceContext& ctx) {
        if (!m_enabled) return;

        auto& input = kx::Input::InputManager::Get();

        // Track keyboard input
        for (int i = 0; i < 256; ++i) {
            if (input.IsKeyPressed(i)) {
                m_debugInfo.lastKeyDown = i;
            }
        }

        // Track mouse motion
        auto mouseMotion = input.GetMouseMotion();
        m_debugInfo.mouseX = static_cast<float>(mouseMotion.dx);
        m_debugInfo.mouseY = static_cast<float>(mouseMotion.dy);

        // Track gamepad if connected
        if (input.IsGamepadConnected()) {
            auto gamepad = input.GetGamepadState();
            
            m_debugInfo.gamepadStickX = gamepad.x / 1000.0f;
            m_debugInfo.gamepadStickY = gamepad.y / 1000.0f;
            
            m_debugInfo.gamepadButtons = 0;
            for (int i = 0; i < 32; ++i) {
                if (gamepad.buttons[i]) {
                    m_debugInfo.gamepadButtons |= (1 << i);
                }
            }
        }

        // Example: Use input to control something
        // Replace this with your actual feature logic

        // Example 1: WASD movement
        if (input.IsKeyDown(0x57)) {  // VK_W = 0x57
            LOG_DEBUG("[InputTestFeature] W key held");
        }

        // Example 2: Mouse button check
        if (input.IsMouseButtonDown(RI_MOUSE_BUTTON_1_DOWN)) {
            LOG_DEBUG("[InputTestFeature] Left mouse button held");
        }

        // Example 3: Gamepad button check
        if (input.IsGamepadConnected() && input.IsGamepadButtonDown(0)) {
            LOG_DEBUG("[InputTestFeature] Gamepad Button A pressed");
        }
    }

    void InputTestFeature::RenderDrawList(ImDrawList* drawList, const ServiceContext& ctx) {
        // Render any 2D graphics here
        // Example: Draw a crosshair at mouse position
    }

    void InputTestFeature::OnMenuRender() {
        if (!ImGui::CollapsingHeader("Input Debug", ImGuiTreeNodeFlags_DefaultOpen)) {
            return;
        }

        auto& input = kx::Input::InputManager::Get();

        // Enable/disable
        ImGui::Checkbox("Enable##InputTest", &m_enabled);
        ImGui::Checkbox("Show Debug Info", &m_showDebugInfo);

        if (!m_showDebugInfo) return;

        ImGui::Separator();

        // Keyboard section
        ImGui::TextColored(ImVec4(0.2f, 0.8f, 1.0f, 1.0f), "Keyboard Input");
        if (m_debugInfo.lastKeyDown != -1) {
            ImGui::Text("Last Key Down: 0x%02X (%d)", m_debugInfo.lastKeyDown, m_debugInfo.lastKeyDown);

            // Try to display the character if it's a letter
            if (m_debugInfo.lastKeyDown >= 0x41 && m_debugInfo.lastKeyDown <= 0x5A) {
                char letter = 'A' + (m_debugInfo.lastKeyDown - 0x41);
                ImGui::SameLine();
                ImGui::Text("('%c')", letter);
            }
        }
        
        // Show key states for common keys
        const int commonKeys[] = {
            0x57, 0x41, 0x53, 0x44,  // W, A, S, D (0x57, 0x41, 0x53, 0x44)
            VK_SPACE, VK_LSHIFT, VK_LCONTROL,
            VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT
        };

        ImGui::Text("Common Keys:");
        for (int key : commonKeys) {
            bool isDown = input.IsKeyDown(key);
            const char* keyName = "?";

            if (key >= 0x41 && key <= 0x5A) keyName = "?";
            else if (key == VK_SPACE) keyName = "Space";
            else if (key == VK_LSHIFT) keyName = "LShift";
            else if (key == VK_LCONTROL) keyName = "LCtrl";
            else if (key == VK_UP) keyName = "Up";
            else if (key == VK_DOWN) keyName = "Down";
            else if (key == VK_LEFT) keyName = "Left";
            else if (key == VK_RIGHT) keyName = "Right";

            ImGui::Text("  %s: %s", keyName, isDown ? "DOWN" : "up");
        }

        ImGui::Separator();

        // Mouse section
        ImGui::TextColored(ImVec4(0.2f, 1.0f, 0.2f, 1.0f), "Mouse Input");
        ImGui::Text("Motion DX: %.0f, DY: %.0f", m_debugInfo.mouseX, m_debugInfo.mouseY);
        ImGui::Text("Left Button: %s", input.IsMouseButtonDown(RI_MOUSE_BUTTON_1_DOWN) ? "DOWN" : "up");
        ImGui::Text("Right Button: %s", input.IsMouseButtonDown(RI_MOUSE_BUTTON_2_DOWN) ? "DOWN" : "up");
        ImGui::Text("Middle Button: %s", input.IsMouseButtonDown(RI_MOUSE_BUTTON_3_DOWN) ? "DOWN" : "up");

        ImGui::Separator();

        // Gamepad section
        ImGui::TextColored(ImVec4(1.0f, 0.8f, 0.2f, 1.0f), "Gamepad Input");
        
        if (input.IsGamepadConnected()) {
            ImGui::TextColored(ImVec4(0.2f, 1.0f, 0.2f, 1.0f), "Connected");
            
            ImGui::Text("Stick L: X=%.2f, Y=%.2f", m_debugInfo.gamepadStickX, m_debugInfo.gamepadStickY);
            
            auto gamepad = input.GetGamepadState();
            ImGui::Text("Stick R: X=%.2f, Y=%.2f", gamepad.rx / 1000.0f, gamepad.ry / 1000.0f);
            ImGui::Text("Triggers: Z=%.2f, RZ=%.2f", gamepad.z / 1000.0f, gamepad.rz / 1000.0f);
            
            // Display POV hat state
            if (gamepad.pov != -1) {
                int angle = gamepad.pov / 100;
                ImGui::Text("POV: %d°", angle);
            } else {
                ImGui::Text("POV: Centered");
            }
            
            // Display button states
            ImGui::Text("Buttons Active: 0x%08X", m_debugInfo.gamepadButtons);
            for (int i = 0; i < 16; ++i) {
                if (gamepad.buttons[i]) {
                    ImGui::SameLine();
                    ImGui::Text("[B%d]", i);
                }
            }
            
            // Show button legend
            ImGui::TextDisabled("(Button mapping may vary by device)");
            ImGui::BulletText("Button 0 = A / Cross");
            ImGui::BulletText("Button 1 = B / Circle");
            ImGui::BulletText("Button 2 = X / Square");
            ImGui::BulletText("Button 3 = Y / Triangle");
        } else {
            ImGui::TextColored(ImVec4(1.0f, 0.2f, 0.2f, 1.0f), "Not Connected");
        }
    }

    bool InputTestFeature::OnInput(UINT message, WPARAM wParam, LPARAM lParam) {
        // You can handle specific messages here if needed
        // Return true to consume the input (block it from propagating)
        
        // Example: Block ESC key
        if (message == WM_KEYDOWN && wParam == VK_ESCAPE) {
            // Consume the escape key
            // return true;
        }

        return false; // Don't consume by default
    }

    void InputTestFeature::LoadSettings(const nlohmann::json& j) {
        if (j.contains("enabled")) {
            m_enabled = j["enabled"];
        }
        if (j.contains("showDebugInfo")) {
            m_showDebugInfo = j["showDebugInfo"];
        }
    }

    void InputTestFeature::SaveSettings(nlohmann::json& j) {
        j["enabled"] = m_enabled;
        j["showDebugInfo"] = m_showDebugInfo;
    }

} // namespace kx::Features
