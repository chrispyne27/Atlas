#ifndef AURORA_ASSET_CACHE_HPP
#define AURORA_ASSET_CACHE_HPP
namespace aurora {
// Unrelated subsystem for measuring irrelevant context selection.
class AssetCache {
    int ids_[4];
    int next_;
public:
    AssetCache();
    void insert(int id);
    bool contains(int id) const;
    int capacity() const;
};
}
#endif
