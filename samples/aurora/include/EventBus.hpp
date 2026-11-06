#ifndef AURORA_EVENT_BUS_HPP
#define AURORA_EVENT_BUS_HPP
#include "Geometry.hpp"
namespace aurora {
struct ViewportChanged { Size size; };
class EventBus {
    int count_;
    Size last_;
public:
    EventBus();
    void publish(const ViewportChanged& event);
    int count() const;
    Size lastSize() const;
};
}
#endif
