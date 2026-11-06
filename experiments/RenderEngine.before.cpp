#include "RenderEngine.hpp"
namespace aurora {
RenderEngine::RenderEngine(EventBus& events, UILayer& ui)
    : events_(events), ui_(ui), viewport_{1, 1} {}
void RenderEngine::resize(Size requested) {
    // Existing implementation: the UI clamps, but viewport and event do not.
    viewport_ = requested;
    ui_.relayout(requested);
    events_.publish(ViewportChanged{viewport_});
}
Size RenderEngine::viewport() const { return viewport_; }
WindowController::WindowController(RenderEngine& engine) : engine_(engine) {}
void WindowController::onSizeChanged(int width, int height) {
    engine_.resize(Size{width, height});
}
}
