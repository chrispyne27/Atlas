#ifndef AURORA_UI_LAYER_HPP
#define AURORA_UI_LAYER_HPP
#include "Geometry.hpp"
namespace aurora {
class LayoutEngine {
public:
    Rect resolve(Size available) const;
};
class UILayer {
    LayoutEngine layout_;
    Rect root_;
public:
    UILayer();
    void relayout(Size available);
    Rect bounds() const;
};
}
#endif
