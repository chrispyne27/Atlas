#include "UILayer.hpp"
namespace aurora {
Rect LayoutEngine::resolve(Size available) const {
    return Rect{0, 0, Geometry::clampDimension(available.width),
                      Geometry::clampDimension(available.height)};
}
UILayer::UILayer() : root_{0, 0, 1, 1} {}
void UILayer::relayout(Size available) {
    root_ = layout_.resolve(available);
}
Rect UILayer::bounds() const { return root_; }
}
