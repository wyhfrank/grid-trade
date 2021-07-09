
# Legends

```
o: buy orders
x: sell orders
O: traded buy orders
X: traded sell orders
.: current price
[: best bid (buy order) price
]: best ask (sell order) price
+: new buy order to be created
-: new sell order to be created
!: create a non post_only order
```

### Type 1: Normal case

In the case of traded sell order
> Condition: `new_price > trade_order_price and best_ask > to_create_order_price`

> Action: Refill a buy order based on traded_order_price

```
        o   o   o [ . ] x   x   x       
        o   o   o       X[.]x   x       
        o   o   o   +   X[.]x   x               
        o   o   o   o    [.]x   x               
```

```
        o   o   o [ . ] x   x   x       
        o   o   o [     X .]x   x       
        o   o   o [ +   X .]x   x               
        o   o   o [ o     .]x   x               
```

### Type 2: Irregular price but post_only creatable

> Condition: `new_price < trade_order_price and best_ask > to_create_order_price`

> Action: Refill a buy order based on traded_order_price

```
        o   o   o [ . ] x   x   x       
        o   o   o [   . X  ]x   x       
        o   o   o [ + . X  ]x   x               
        o   o   o [ o .    ]x   x               
```

### Type 3: Irregular price and post_only NOT creatable

> Condition: `new_price < trade_order_price and best_ask < to_create_order_price`

#### Solution 1: create a non post_only buy order and a post_only sell price

> Action: Create a non post_only buy order (will be executed instantly) and, create a post_only sell price right on the traded order

```
        o   o   o [ . ] x   x   x       
        o   o   o[]   . X   x   x       
        o   o   o[] ! . -   x   x       
        o   o   o[.]    x   x   x       
```

