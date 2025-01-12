#!/usr/bin/env python3

from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from dataclasses import dataclass
from datetime import datetime, time
import sys
import traceback
from typing import NotRequired, TypedDict, cast

parser = argparse.ArgumentParser()
parser.add_argument("usage_file", help="Path to usage CSV file")
parser.add_argument("--current_plan", help="Required to analyse load shift data", required=False)

args = parser.parse_args()

class Prices(TypedDict):
    name: str
    variable: NotRequired[float]
    daily: NotRequired[float]
    surcharge: NotRequired[float]
    bonus: NotRequired[float]

class Plan:
    
    def __init__(self, prices: Prices, custom: bool):
        self.prices = prices
        self.custom = custom

    def variable(self, date: datetime) -> float:
        try:    
            return self.prices['variable'] # type: ignore
        except:
            raise NotImplementedError(f'No variable price set for {type(self).__name__}')   

    def daily(self, date: datetime) -> float:
        try:
            return self.prices['daily'] # type: ignore
        except:
            raise NotImplementedError(f'No daily price set for {type(self).__name__}')
    
    def surcharge(self) -> float:
        if self.prices:
            return self.prices.get('surcharge', 0)
        return 0
    
    def bonus(self) -> float:
        if self.prices:
            return self.prices.get('bonus', 0)
        return 0

    def daily_total(self, half_hour_totals: list[float]) -> float:
        return sum(half_hour_totals)

    def total(self, subtotal: float) -> float:
        return subtotal * (1 + self.surcharge())


class ContactGoodCharge(Plan):

    def variable(self, date: datetime) -> float:
        if (date.time() >= time(7, 0) and date.time() < time(21, 0)):
            return self.prices['variable'] # type: ignore
        return self.prices['offpeak'] # type: ignore


class ContactGoodChargeLowUser(ContactGoodCharge):
    pass


class ContactGoodNights(Plan):

    def variable(self, date: datetime) -> float:
        # free power 9pm to midnight
        if date.time() >= time(21, 0) and date.time() <= time(23, 59):
            return 0
        return self.prices['variable'] # type: ignore


class ContactGoodNightsLowUser(ContactGoodNights):
    pass


class ContactGoodWeekends(Plan):
    
    def variable(self, date: datetime) -> float:
        # free power 9am to 5pm on weekends
        if date.weekday() >= 5 and date.time() >= time(9, 0) and date.time() < time(17, 0):
            return 0
        return self.prices['variable'] # type: ignore


class ContactGoodWeekendsLowUser(ContactGoodWeekends):
    pass


class ElectricKiwi(Plan):

    def variable(self, date: datetime) -> float:
        # peak is Weekdays 7am-9am, 5pm-9pm
        if date.weekday() >= 5:
            return self.prices['offpeak'] # type: ignore
        if (date.time() >= time(7, 0) and date.time() < time(9, 0)) \
            or (date.time() >= time(17, 0) and date.time() < time(21, 0)):
            return self.prices['variable'] # type: ignore
        return self.prices['offpeak'] # type: ignore

    def daily_total(self, half_hour_totals: list[float]) -> float:
        # Consider free hour to be most expensive off peak

        if len(half_hour_totals) != 48:
            # print('found day with wrong number of half hours')
            return sum(half_hour_totals)

        max_hour_value = 0
        max_hour = 0
        for n in range(24):
            if (n >= 7 and n < 9) or (n >= 17 and n < 21):
                # peak
                continue
            hour_total = sum(half_hour_totals[n * 2:n * 2 + 2])
            if hour_total > max_hour_value:
                max_hour_value = hour_total
                max_hour = n

        return sum([ 
            sum(half_hour_totals[n * 2:n * 2 + 2])
            for n in range(24) 
            if n != max_hour
        ])


class ElectricKiwiKiwi(ElectricKiwi):
    pass


class ElectricKiwiKiwiLowUser(ElectricKiwi):
    pass


class ElectricKiwiMoveMaster(ElectricKiwi):

    def variable(self, date: datetime) -> float:
        if date.weekday() < 5 and \
            ((date.time() >= time(7, 0) and date.time() < time(9, 0)) \
            or (date.time() >= time(17, 0) and date.time() < time(21, 0))):
            return self.prices['variable'] # type: ignore
        if (date.time() >= time(9, 0) and date.time() < time(17,0)) \
            or (date.time() >= time(21, 0) and date.time() < time(23, 0)):
            # off peak shoulder
            return self.prices['offpeak'] # type: ignore
        # off peak night
        return self.prices['night'] # type: ignore


class ElectricKiwiMoveMasterLowUser(ElectricKiwiMoveMaster):
    pass
    

class ElectricKiwiPrepay300(ElectricKiwi):
    pass


class ElectricKiwiPrepay300LowUser(ElectricKiwiPrepay300):
    pass


class FlickOffPeak(Plan):

    def variable(self, date: datetime) -> float:
        if (date.time() >= time(7, 0) and date.time() < time(11, 0)) \
            or (date.time() >= time(17, 0) and date.time() < time(21, 0)):
            return self.prices['variable'] # type: ignore
        else:
            return self.prices['offpeak'] # type: ignore


class FlickOffPeakLowUser(FlickOffPeak):
    pass

class GenesisEV(Plan):
    def variable(self, date: datetime) -> float:
        if date.time() >= time(7, 0) and date.time() < time(21, 0):
            return self.prices['variable'] # type: ignore
        else:
            return self.prices['offpeak'] # type: ignore


class ZEv(Plan):
    def variable(self, date: datetime) -> float:
        if date.time() >= time(3, 0) and date.time() < time(6, 0):
            return 0
        elif date.time() >= time(7, 0) and date.time() < time(21, 0):
            return self.prices['variable'] # type: ignore
        else:
            return self.prices['offpeak'] # type: ignore


class ZEvLowUser(ZEv):
    pass


class OctopusFixed(Plan):


    def variable(self, date: datetime) -> float:
        if date.weekday() < 5:
            if (date.time() >= time(7, 0) and date.time() < time(11, 0)) or \
                (date.time() >= time(17, 0) and date.time() < time(21, 0)):
                return self.prices['variable'] # type: ignore
            elif (date.time() >= time(11, 0) and date.time() < time(17, 0)) or \
                (date.time() >= time(21, 0) and date.time() < time(23, 0)):
                return self.prices['offpeak'] # type: ignore
            else:
                return self.prices['night'] # type: ignore
        else:
            # Weekend
            if (date.time() >= time(7, 0) and date.time() < time(23, 0)):
                return self.prices['offpeak'] # type: ignore
            else:
                return self.prices['night'] # type: ignore


class OctopusFixedLowUser(OctopusFixed):
    pass


DATETIME_FORMATS = [
    r'%d/%m/%Y %H:%M:%S',
    r'%d/%m/%Y %H:%M'
]

PERIOD_START_COLUMN = 9
PERIOD_END_COLUMN = 10
USAGE_COLUMN = 12

TOTAL_TIME_PERIOD = 31_536_000 # 1 year

def parse_datetime(s: str) -> datetime:
    for fmt in DATETIME_FORMATS:
        try:
            # print(f'Try parse "{s}" with "{fmt}"')
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f'Could not parse datetime {s}')

def try_float(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def parse_days(days: str) -> list[int]:
    DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

    ranges = days.split(',')
    result = []
    for r in ranges:
        if '-' in r:
            start, end = r.split('-')
            start_index = DAYS.index(start)
            end_index = DAYS.index(end)
            result.extend(range(start_index, end_index + 1))
        else:
            result.append(DAYS.index(r))
    return result


plans = []
usage_data = []
load_shifts = []

total_time = 0
results = []

# Load pricing plans
with open('prices.csv', 'r') as f:
    prices_csv = csv.DictReader(f)
    for row in prices_csv:
        # convert everything to floats, apart from name
        prices = {}
        name = ''
        for k in row:
            v = row[k].strip()
            if v == '':
                continue

            if k.strip() == 'name':
                name = v
            else:
                v = try_float(row[k].strip())
            if (v is not None) and (v != ''):
                prices[k.strip()] = v

        # print(prices)

        plan_class = globals().get(name)
        if plan_class:
            plan = plan_class(cast(Prices, prices), custom=True)
        else:
            plan = Plan(cast(Prices, prices), custom=False)

        plans.append(plan)

# Load usage data
with open(args.usage_file) as f:
    reader = csv.reader(f)
    header = next(reader)
    period_start = datetime.now()

    for row in reader:
        last_row = row
        start_str = row[PERIOD_START_COLUMN]
        datetime_str = row[PERIOD_END_COLUMN]
        usage = float(row[USAGE_COLUMN])

        period_start = parse_datetime(start_str)
        period_end = parse_datetime(datetime_str)
        total_time += (period_end - period_start).seconds
        usage_data.append((period_start, period_end, usage))

# WIP load shifts

# @dataclass
# class LoadShift:
#     name: str
#     days: list[int]
#     times: int
#     minutes: int
#     usage: float

# @dataclass
# class PricePeriod:
#     period_start: datetime
#     period_end: datetime | None
#     price: float
#     usage: float

# if args.current_plan:
#     current_plan = next((plan for plan in plans if plan.prices['name'] == args.current_plan), None)
#     if current_plan is None:
#         print(f'Could not find plan {args.current_plan}', file=sys.stderr)
#         sys.exit(1)

#     with open('load_shift.csv', 'r') as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             name = row['name']
#             days = parse_days(row['days'])
#             times = int(row['times'])
#             minutes = int(row['minutes'])
#             usage = float(row['kwh'])
#             load_shifts.append(LoadShift(name, days, times, minutes, usage))

#     total_data = {}
#     week_data = []

#     open_period = None

#     for period_start, period_end, usage in usage_data:
#         price = current_plan.variable(period_start)
#         if open_period is None or open_period.price != price:
#             if open_period is not None:
#                 # Close period
#                 open_period.period_end = period_start
#                 week_data.append(open_period)

#                 # ~Allocate load shifts to cheapest periods~
#                 # Remove load shifts from cheapest periods
#                 week_shifts = deepcopy(load_shifts)
#                 while True:
#                     for load in week_shifts:
#                         pass

#             price_period = PricePeriod(period_start, None, price, usage)
#         else:
#             price_period.usage += usage


for plan in plans:

    last_row = None
    try:
        total_cost = 0
        current_day = None
        day_prices = []

        for period_start, period_end, usage in usage_data:

            if (period_end - period_start).seconds > 3600:
                continue

            if current_day is None:
                current_day = period_start.date()

            period_usage_charge = plan.variable(period_start) * usage
            
            if (period_start.date() == current_day):
                day_prices.append(period_usage_charge)
            else:
                total_cost += plan.daily_total(day_prices) + plan.daily(period_end)
                day_prices = [period_usage_charge]
                current_day = period_start.date()

        # close final day
        total_cost += plan.daily_total(day_prices) + plan.daily(period_start)
        
        subtotal = plan.total(total_cost)
        scalar = TOTAL_TIME_PERIOD / total_time

        bonus = plan.bonus() * 100
        year_cost = (subtotal * scalar) - bonus
        period_cost = year_cost / scalar

        results.append((period_cost, year_cost, plan.prices['name'], plan.custom))
    except Exception as e:
        print(f'Error processing {plan.prices["name"]}: {e}')
        print(f'Last row: {last_row}')
        traceback.print_exc()

results.sort()
print(f'Days: {total_time / 86400:.2f}')
for (period_cost, year_cost, provider_name, custom) in results:
    star = '*' if custom else ''
    print(f'{provider_name}{star}: {period_cost / 100:.2f} ({year_cost / 100:.2f})')
print('* = custom logic used', file=sys.stderr)
