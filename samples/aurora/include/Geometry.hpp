#ifndef AURORA_GEOMETRY_HPP
#define AURORA_GEOMETRY_HPP
namespace aurora {
struct Size { int width; int height; };
struct Rect { int x; int y; int width; int height; };
class Geometry {
public:
    // Shared policy: valid drawable dimensions are inclusive 1..8192.
    static int clampDimension(int value);
    static float clampDimension(float value);
    static bool contains(const Rect& bounds, int x, int y);
};
}
#endif
