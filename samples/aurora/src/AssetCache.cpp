#include "AssetCache.hpp"
namespace aurora {
AssetCache::AssetCache() : ids_{-1, -1, -1, -1}, next_(0) {}
void AssetCache::insert(int id) {
    if (contains(id)) return;
    ids_[next_] = id;
    next_ = (next_ + 1) % capacity();
}
bool AssetCache::contains(int id) const {
    for (int i = 0; i < capacity(); ++i) {
        if (ids_[i] == id) return true;
    }
    return false;
}
int AssetCache::capacity() const { return 4; }
}
