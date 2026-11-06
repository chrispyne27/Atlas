#include "EventBus.hpp"
namespace aurora {
EventBus::EventBus() : count_(0), last_{0, 0} {}
void EventBus::publish(const ViewportChanged& event) {
    last_ = event.size;
    ++count_;
}
int EventBus::count() const { return count_; }
Size EventBus::lastSize() const { return last_; }
}
