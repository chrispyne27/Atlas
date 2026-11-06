#include "RenderEngine.hpp"
#include "AssetCache.hpp"
namespace aurora {
namespace tests {
bool nominalResize() {
    EventBus events; UILayer ui; RenderEngine engine(events, ui);
    WindowController window(engine);
    window.onSizeChanged(1280, 720);
    return engine.viewport().width == 1280 && ui.bounds().height == 720 &&
           events.count() == 1 && events.lastSize().height == 720;
}
bool layoutClamps() {
    LayoutEngine layout;
    Rect bounds = layout.resolve(Size{-9, 9000});
    return bounds.width == 1 && bounds.height == 8192;
}
bool cacheEvicts() {
    AssetCache cache;
    for (int i = 1; i <= 5; ++i) cache.insert(i);
    return !cache.contains(1) && cache.contains(5) && cache.capacity() == 4;
}
bool zeroResize() {
    EventBus events; UILayer ui; RenderEngine engine(events, ui);
    engine.resize(Size{0, 0});
    return engine.viewport().width == 1 && engine.viewport().height == 1 &&
           ui.bounds().width == 1 && events.lastSize().width == 1;
}
bool negativeResize() {
    EventBus events; UILayer ui; RenderEngine engine(events, ui);
    engine.resize(Size{-100, -5});
    return engine.viewport().width == 1 && engine.viewport().height == 1 &&
           ui.bounds().height == 1 && events.lastSize().height == 1;
}
bool oversizeResize() {
    EventBus events; UILayer ui; RenderEngine engine(events, ui);
    engine.resize(Size{9000, 12000});
    return engine.viewport().width == 8192 && engine.viewport().height == 8192 &&
           ui.bounds().width == 8192 && events.lastSize().height == 8192;
}
bool eventMatchesLayout() {
    EventBus events; UILayer ui; RenderEngine engine(events, ui);
    engine.resize(Size{0, 300});
    return events.count() == 1 && events.lastSize().width == ui.bounds().width &&
           events.lastSize().height == ui.bounds().height;
}
bool repeatedResize() {
    EventBus events; UILayer ui; RenderEngine engine(events, ui);
    engine.resize(Size{100, 200});
    engine.resize(Size{300, 400});
    return events.count() == 2 && engine.viewport().width == 300 &&
           ui.bounds().height == 400 && events.lastSize().width == 300;
}
}
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    using namespace aurora::tests;
    switch (argv[1][0]) {
        case '0': return nominalResize() ? 0 : 1;
        case '1': return layoutClamps() ? 0 : 1;
        case '2': return cacheEvicts() ? 0 : 1;
        case '3': return zeroResize() ? 0 : 1;
        case '4': return negativeResize() ? 0 : 1;
        case '5': return oversizeResize() ? 0 : 1;
        case '6': return eventMatchesLayout() ? 0 : 1;
        case '7': return repeatedResize() ? 0 : 1;
        default: return 2;
    }
}
