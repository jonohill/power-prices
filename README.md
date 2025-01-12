# power-prices

A very hacky script to compare power prices based on actual usage. Input is a path to a CSV file in [Electricity Authority EIEP13A](https://www.ea.govt.nz/assets/dms-assets/30/EIEP13A-HHR-and-NHH-combined-v1.4.pdf) format.

## Adding plans/prices

Add the plan and prices to `prices.csv`. `name` is required. All prices are in cents incl GST. There are lots there already, but the prices won't be up to date and are probably not the same as your area.

If the plan needs special logic, e.g. for off peak periods or free periods, create a python class with the same name as the plan, derive Plan, and override any required methods. The script already contains a number of plans that can be used as examples.

All fields apart from `name` are optional in the CSV. You can also provide:
- `variable` - price per kWh. Must be set unless a custom class supplies this.
- `fixed` - daily fixed charge. Must be set unless a custom class supplies this.
- `surcharge` - a percentage surcharge (or discount if negative) to be added to the total cost. Optional.
- `bonus` - a fixed discount to be subtracted from the total cost. Optional.

Nothing else has special meaning globally, but the whole row is available to a custom class as `self.prices`. By convention, a lot of custom classes use `offpeak` and `night` as special fields.
All fields are treated as numeric.
