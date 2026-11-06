#ifndef AURORA_RENDER_ENGINE_HPP
#define AURORA_RENDER_ENGINE_HPP
#include "Geometry.hpp"
#include "EventBus.hpp"
#include "UILayer.hpp"
namespace aurora {
class RenderEngine {
    EventBus& events_;
    UILayer& ui_;
    Size viewport_;
public:
    RenderEngine(EventBus& events, UILayer& ui);
    void resize(Size requested);
    Size viewport() const;
};
class WindowController {
    RenderEngine& engine_;
public:
    explicit WindowController(RenderEngine& engine);
    void onSizeChanged(int width, int height);
};
}
#endif
