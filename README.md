## Get Started

1. Copy `configs/config.sample.yml` to `configs/config.yml` and enter your configurations
2. (optional) Add `configs/serviceAccountKey.json` file for Google firebase service
3. Run following commands

``` sh
# Build the docker image
make build

# Run the image
make run
```

## TODO

- [ ] Log the full lifecycle of an order (creation -> traded -> removed)
- [x] Add option to output logs into files
- [ ] Better way of refilling orders
  - Current price may go up and down so fast (within one sync) that orders were not created properly
  - [x] Detect and log such situations
- [x] Bug: orders are not refilled properly
- [x] Bug: duplicate orders exist
- [x] Format prices for orders and params (remove floating point)
- [ ] Reset the bot only when price changed over a certain degree (instead of doing this by time interval)
- [ ] Calculate earn rate
- [ ] Recover bot from db if stopped. (perhaps not needed)
- [x] Discord notification
