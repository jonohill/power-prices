#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from datetime import datetime, time
from typing import Callable, List, Tuple, cast

parser = argparse.ArgumentParser()
parser.add_argument("prices_file", help="Path to prices CSV file")

args = parser.parse_args()

class Provider:
    
    def get_variable_price(self, date: datetime) -> float:
        raise NotImplementedError()

    def get_fixed_price(self, date: datetime) -> float:
        raise NotImplementedError()

    def calculate_daily_total(self, half_hour_totals: list[float]) -> float:
        return sum(half_hour_totals)

    def calculate_total(self, subtotal: float) -> float:
        return subtotal
    
PROVIDERS: list[Provider] = []


# class Powershop(Provider):

#     def get_variable_price(self, date: datetime) -> float:

#         # Price table from https://secure.powershop.co.nz/properties/388311/rates
#         prices = """Apr	May	Jun	Jul	Aug	Sep	Oct	Nov	Dec	Jan	Feb	Mar
#             16.49	17.21	16.96	16.64	16.11	15.11	14.58	13.88	13.51	13.98	14.12	15.35
#             25.4	26.12	25.87	25.55	25.02	24.02	23.49	22.79	22.42	22.89	23.03	24.27"""
#         lines = prices.split('\n')
#         months = lines[0].split()
#         off_peak = lines[1].split()
#         peak = lines[2].split()

#         month = months.index(date.strftime('%b'))
#         day_of_week = date.weekday()

#         if day_of_week < 5: # weekdays only
#             if (date.time() >= time(7, 0) and date.time() < time(11, 0)) or \
#                 (date.time() >= time(17, 0) and date.time() < time(21, 0)):
#                 # Peak
#                 return float(peak[month])
#         # else offpeak
#         return float(off_peak[month])

#     def get_fixed_price(self, _date: datetime) -> float:
#         return 215.05

#     def calculate_total(self, subtotal: float) -> float:
#         # assume 1% discount
#         return subtotal * 0.99


class Contact(Provider):

    def calculate_total(self, subtotal: float) -> float:
        # credit card fee
        return subtotal * 1.0095

class ContactGoodNights(Contact):

    def get_non_free_variable_price(self) -> float:
        return 22.54

    def get_variable_price(self, date: datetime) -> float:
        # free power 9pm to midnight
        if date.time() >= time(21, 0) and date.time() <= time(23, 59):
            return 0
        return self.get_non_free_variable_price()
    
    def get_fixed_price(self, _: datetime) -> float:
        return 240.6
PROVIDERS.append(ContactGoodNights())

class ContactGoodNightsLowUser(ContactGoodNights):

    def get_non_free_variable_price(self) -> float:
        return 30.245
    
    def get_fixed_price(self, _: datetime) -> float:
        return 103.5
PROVIDERS.append(ContactGoodNightsLowUser())

class ContactDreamCharge(Contact):

    def peak(self):
        return 23.69
    
    def offpeak(self):
        return 14.26

    def get_variable_price(self, date: datetime) -> float:
        # peak 7am-11pm
        if (date.time() >= time(7, 0) and date.time() < time(23, 0)):
            return self.peak()
        else:
            return self.offpeak()
        
    def get_fixed_price(self, _: datetime) -> float:
        return 174.9
PROVIDERS.append(ContactDreamCharge())
    
class ContactDreamChargeLowUser(ContactDreamCharge):

    def peak(self):
        return 26.795
    
    def offpeak(self):
        return 17.365
    
    def get_fixed_price(self, _: datetime) -> float:
        return 103.5
PROVIDERS.append(ContactDreamChargeLowUser())
    
class ContactEverydayBonusFixed(Contact):

    def get_variable_price(self, date: datetime) -> float:
        return 20.47 + 0.161
    
    def get_fixed_price(self, date: datetime) -> float:
        return 228.2
    
    def calculate_total(self, subtotal: float) -> float:
        # 2% discount
        subtotal *= 0.98
        return super().calculate_total(subtotal)
PROVIDERS.append(ContactEverydayBonusFixed())
    
class ContactEverydayBonusLowUser(ContactEverydayBonusFixed):

    def get_variable_price(self, date: datetime) -> float:
        return 25.99 + 0.161
    
    def get_fixed_price(self, date: datetime) -> float:
        return 103.5
PROVIDERS.append(ContactEverydayBonusLowUser())
    

class ElectricKiwi(Provider):

    def calculate_daily_total(self, half_hour_totals: list[float]) -> float:
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

class ElectricKiwiStayAhead(ElectricKiwi):

    def get_variable_price(self, _: datetime) -> float:
        return 27.41

    def get_fixed_price(self, _: datetime) -> float:
        return 263

    def calculate_total(self, subtotal: float) -> float:
        # Every $220 costs $200
        return subtotal * (200/220)
PROVIDERS.append(ElectricKiwiStayAhead())
    
class ElectricKiwiStayAheadLowUser(ElectricKiwiStayAhead):

    def get_variable_price(self, _: datetime) -> float:
        return 38.85

    def get_fixed_price(self, _: datetime) -> float:
        return 37
PROVIDERS.append(ElectricKiwiStayAheadLowUser())

class ElectricKiwiMoveMaster(ElectricKiwi):

    def peak(self):
        return 30.56
    
    def night(self):
        return 15.28
    
    def shoulder(self):
        return 21.39

    def get_variable_price(self, date: datetime) -> float:
        if (date.time() >= time(7, 0) and date.time() < time(9, 0)) \
            or (date.time() >= time(17, 0) and date.time() < time(21, 0)):
            return self.peak()
        if (date.time() >= time(9, 0) and date.time() < time(17,0)) \
            or (date.time() >= time(21, 0) and date.time() < time(23, 0)):
            # off peak shoulder
            return self.shoulder()
        # off peak night
        return self.night()

    def get_fixed_price(self, _: datetime) -> float:
        return 239

PROVIDERS.append(ElectricKiwiMoveMaster())

class ElectricKiwiMoveMasterLowUser(ElectricKiwiMoveMaster):

    def peak(self):
        return 44.44
    
    def night(self):
        return 22.22
    
    def shoulder(self):
        return 31.10
    
    def get_fixed_price(self, _: datetime) -> float:
        return 34
    
PROVIDERS.append(ElectricKiwiMoveMasterLowUser())


class Frank(Provider):

    def get_variable_price(self, _: datetime) -> float:
        return 22.31

    def get_fixed_price(self, _: datetime) -> float:
        return 155.25

PROVIDERS.append(Frank())

class FrankLowUser(Frank):

    def get_variable_price(self, _: datetime) -> float:
        return 26.22

    def get_fixed_price(self, _: datetime) -> float:
        return 69

PROVIDERS.append(FrankLowUser())


class FlickOffPeak(Provider):

    def peak(self):
        return 23.38
    
    def offpeak(self):
        return 13.91

    def get_variable_price(self, date: datetime) -> float:
        if (date.time() >= time(7, 0) and date.time() < time(11, 0)) \
            or (date.time() >= time(17, 0) and date.time() < time(21, 0)):
            return self.peak()
        else:
            return self.offpeak()

    def get_fixed_price(self, _: datetime) -> float:
        return 253

PROVIDERS.append(FlickOffPeak())

class FlickOffPeakLowUser(FlickOffPeak):

    def peak(self):
        return 30.19
    
    def offpeak(self):
        return 20.72

    def get_fixed_price(self, _: datetime) -> float:
        return 103.5
    
class FlickFlat(Provider):

    def get_variable_price(self, _: datetime) -> float:
        return 16.75

    def get_fixed_price(self, _: datetime) -> float:
        return 253
    
PROVIDERS.append(FlickFlat())

class FlickFlatLowUser(FlickFlat):

    def get_variable_price(self, _: datetime) -> float:
        return 23.56

    def get_fixed_price(self, _: datetime) -> float:
        return 103.5
    
PROVIDERS.append(FlickFlatLowUser())


# class MercuryTwoYear(Provider):

#     def get_variable_price(self, date: datetime) -> float:
#         return 16.49 + 0.12

#     def get_fixed_price(self, date: datetime) -> float:
#         return 235.69

#     def calculate_total(self, subtotal: float) -> float:
#         return (subtotal * 0.88 * 1.15 - 10000) # * gst - discount - sign up bonus


class OctopusFixed(Provider):

    PEAK = 27.416
    OFF_PEAK = 21.666
    NIGHT = 13.708

    def get_variable_price(self, date: datetime) -> float:
        if date.weekday() < 5:
            if (date.time() >= time(7, 0) and date.time() < time(11, 0)) or \
                (date.time() >= time(17, 0) and date.time() < time(21, 0)):
                return self.PEAK
            elif (date.time() >= time(11, 0) and date.time() < time(17, 0)) or \
                (date.time() >= time(21, 0) and date.time() < time(23, 0)):
                return self.OFF_PEAK
            else:
                return self.NIGHT
        else:
            # Weekend
            if (date.time() >= time(7, 0) and date.time() < time(23, 0)):
                return self.OFF_PEAK
            else:
                return self.NIGHT

    def get_fixed_price(self, date: datetime) -> float:
        return 247.25

PROVIDERS.append(OctopusFixed())

class OctopusLowUser(OctopusFixed):

    PEAK = 35.0405
    OFF_PEAK = 29.2905
    NIGHT = 17.526

    def get_fixed_price(self, date: datetime) -> float:
        return 103.5

PROVIDERS.append(OctopusLowUser())


class TwoDegrees(Provider):

    def get_variable_price(self, _: datetime) -> float:
        return 24.191 * 1.15

    def get_fixed_price(self, _: datetime) -> float:
        return 212.16 * 1.15
    
    def calculate_total(self, subtotal: float) -> float:
        # $20 off broadband per month
        return subtotal - (20 * 12)


PROVIDERS.append(TwoDegrees())


class TwoDegreesLowerUser(TwoDegrees):

    def get_variable_price(self, _: datetime) -> float:
        return 32.496 * 1.15

    def get_fixed_price(self, _: datetime) -> float:
        return 30 * 1.15
    
PROVIDERS.append(TwoDegreesLowerUser())


DATETIME_FORMAT = r'%d/%m/%Y %H:%M:%S'
PERIOD_START_COLUMN = 9
PERIOD_END_COLUMN = 10
USAGE_COLUMN = 12

results = []

for provider in PROVIDERS:
    total_cost = 0
    current_day = None
    day_prices = []
    with open(args.prices_file) as f:
        reader = csv.reader(f)
        header = next(reader)
        period_start = datetime.now()
        for row in reader:
            start_str = row[PERIOD_START_COLUMN]
            datetime_str = row[PERIOD_END_COLUMN]
            usage = float(row[USAGE_COLUMN])

            period_start = datetime.strptime(start_str, DATETIME_FORMAT)
            period_end = datetime.strptime(datetime_str, DATETIME_FORMAT)
            if (period_end - period_start).seconds > 3600:
                continue

            if current_day is None:
                current_day = period_start.date()
            
            if (period_start.date() == current_day):
                day_prices.append(provider.get_variable_price(period_start) * usage)
            else:
                total_cost += provider.calculate_daily_total(day_prices) + provider.get_fixed_price(period_end)
                day_prices = [provider.get_variable_price(period_start) * usage]
                current_day = period_start.date()
        total_cost += provider.calculate_daily_total(day_prices) + provider.get_fixed_price(period_start)
    total_cost = provider.calculate_total(total_cost)

    results.append((total_cost, type(provider).__name__))

results.sort()
for (total_cost, provider_name) in results:
    print(f'{provider_name}: {total_cost / 100:.2f}')
