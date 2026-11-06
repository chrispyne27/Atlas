#include "Geometry.hpp"
namespace aurora {
int Geometry::clampDimension(int value) {
    if (value < 1) return 1;
    if (value > 8192) return 8192;
    return value;
}
float Geometry::clampDimension(float value) {
    if (value < 1.0f) return 1.0f;
    if (value > 8192.0f) return 8192.0f;
    return value;
}
bool Geometry::contains(const Rect& bounds, int x, int y) {
    return x >= bounds.x && y >= bounds.y &&
           x < bounds.x + bounds.width && y < bounds.y + bounds.height;
}
}
