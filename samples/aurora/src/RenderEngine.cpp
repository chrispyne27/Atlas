#include "RenderEngine.hpp"
namespace aurora {
RenderEngine::RenderEngine(EventBus& events, UILayer& ui)
    : events_(events), ui_(ui), viewport_{1, 1} {}
void RenderEngine::resize(Size requested) {
    // One shared policy keeps viewport, layout, and notification consistent.
    viewport_ = Size{Geometry::clampDimension(requested.width),
                     Geometry::clampDimension(requested.height)};
    ui_.relayout(viewport_);
    events_.publish(ViewportChanged{viewport_});
}
Size RenderEngine::viewport() const { return viewport_; }
WindowController::WindowController(RenderEngine& engine) : engine_(engine) {}
void WindowController::onSizeChanged(int width, int height) {
    engine_.resize(Size{width, height});
}
}
