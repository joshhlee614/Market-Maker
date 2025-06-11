#include <map>
#include <string>
#include <vector>
#include <memory>
#include <stdexcept>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// forward declarations
struct Order;
struct Fill;

// order book side (bids or asks)
enum class Side {
    BUY,
    SELL
};

// represents a single order
struct Order {
    std::string order_id;
    Side side;
    double price;
    double size;
    int64_t timestamp;

    Order(std::string id, Side s, double p, double sz, int64_t ts)
        : order_id(std::move(id)), side(s), price(p), size(sz), timestamp(ts) {}
};

// represents a fill event
struct Fill {
    std::string taker_order_id;
    std::string maker_order_id;
    double price;
    double size;
    int64_t timestamp;

    Fill(std::string taker, std::string maker, double p, double sz, int64_t ts)
        : taker_order_id(std::move(taker)), maker_order_id(std::move(maker)),
          price(p), size(sz), timestamp(ts) {}
};

// price level in the order book
struct PriceLevel {
    std::vector<std::shared_ptr<Order>> orders;
};

// common type for ask book (ascending)
using AskBook = std::map<double, PriceLevel, std::less<double>>;
// common type for bid book (descending)
using BidBook = std::map<double, PriceLevel, std::greater<double>>;

class MatchEngine {
private:
    // price -> orders at that price
    BidBook bids;
    AskBook asks;
    // order_id -> (side, price)
    std::map<std::string, std::pair<Side, double>> order_map;

    std::vector<Fill> match_buy(std::shared_ptr<Order>& order) {
        std::vector<Fill> fills;
        
        for (auto& [price, level] : asks) {
            if (price > order->price) break;
            
            while (!level.orders.empty() && order->size > 0) {
                auto maker = level.orders.front();
                double match_size = std::min(order->size, maker->size);
                
                fills.emplace_back(
                    order->order_id,
                    maker->order_id,
                    price,
                    match_size,
                    order->timestamp
                );
                
                order->size -= match_size;
                maker->size -= match_size;
                
                if (maker->size == 0) {
                    level.orders.erase(level.orders.begin());
                    order_map.erase(maker->order_id);
                    if (level.orders.empty()) {
                        asks.erase(price);
                    }
                }
            }
        }
        
        return fills;
    }
    
    std::vector<Fill> match_sell(std::shared_ptr<Order>& order) {
        std::vector<Fill> fills;
        
        for (auto& [price, level] : bids) {
            if (price < order->price) break;
            
            while (!level.orders.empty() && order->size > 0) {
                auto maker = level.orders.front();
                double match_size = std::min(order->size, maker->size);
                
                fills.emplace_back(
                    order->order_id,
                    maker->order_id,
                    price,
                    match_size,
                    order->timestamp
                );
                
                order->size -= match_size;
                maker->size -= match_size;
                
                if (maker->size == 0) {
                    level.orders.erase(level.orders.begin());
                    order_map.erase(maker->order_id);
                    if (level.orders.empty()) {
                        bids.erase(price);
                    }
                }
            }
        }
        
        return fills;
    }
    
    void add_to_book(const std::shared_ptr<Order>& order) {
        if (order->side == Side::BUY) {
            bids[order->price].orders.push_back(order);
        } else {
            asks[order->price].orders.push_back(order);
        }
        order_map[order->order_id] = {order->side, order->price};
    }

public:
    std::vector<Fill> insert(const std::string& order_id, Side side, 
                            double price, double size, int64_t timestamp) {
        auto order = std::make_shared<Order>(order_id, side, price, size, timestamp);
        std::vector<Fill> fills;
        
        if (side == Side::BUY) {
            fills = match_buy(order);
        } else {
            fills = match_sell(order);
        }
        
        if (order->size > 0) {
            add_to_book(order);
        }
        
        return fills;
    }
    
    bool cancel(const std::string& order_id) {
        auto it = order_map.find(order_id);
        if (it == order_map.end()) {
            return false;
        }
        auto [side, price] = it->second;
        if (side == Side::BUY) {
            auto level_it = bids.find(price);
            if (level_it != bids.end()) {
                auto& orders = level_it->second.orders;
                for (auto order_it = orders.begin(); order_it != orders.end(); ++order_it) {
                    if ((*order_it)->order_id == order_id) {
                        orders.erase(order_it);
                        if (orders.empty()) {
                            bids.erase(level_it);
                        }
                        order_map.erase(it);
                        return true;
                    }
                }
            }
        } else {
            auto level_it = asks.find(price);
            if (level_it != asks.end()) {
                auto& orders = level_it->second.orders;
                for (auto order_it = orders.begin(); order_it != orders.end(); ++order_it) {
                    if ((*order_it)->order_id == order_id) {
                        orders.erase(order_it);
                        if (orders.empty()) {
                            asks.erase(level_it);
                        }
                        order_map.erase(it);
                        return true;
                    }
                }
            }
        }
        return false;
    }
};

PYBIND11_MODULE(match_engine, m) {
    py::enum_<Side>(m, "Side")
        .value("BUY", Side::BUY)
        .value("SELL", Side::SELL)
        .export_values();
    
    py::class_<Fill>(m, "Fill")
        .def_readonly("taker_order_id", &Fill::taker_order_id)
        .def_readonly("maker_order_id", &Fill::maker_order_id)
        .def_readonly("price", &Fill::price)
        .def_readonly("size", &Fill::size)
        .def_readonly("timestamp", &Fill::timestamp);
    
    py::class_<MatchEngine>(m, "MatchEngine")
        .def(py::init<>())
        .def("insert", &MatchEngine::insert)
        .def("cancel", &MatchEngine::cancel);
} 