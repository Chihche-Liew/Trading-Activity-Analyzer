# Trading Activity Analyzer

## Description

A Python class designed to analyze trading volume around specific event dates using CRSP daily stock data from WRDS. The analyzer performs trading volume extraction over custom event windows, supports several normality tests (Jarque-Bera, Shapiro-Wilk, Anderson-Darling), and optionally generates event-aligned trading volume plots. Ideal for event study diagnostics or pre-processing.

## Features

- Event-aligned volume extraction from CRSP using `permno` and event `trans_date`
- Adjustable window before/after each event (e.g., [-5, +5])
- Supports normality testing on volume series:
  - Jarque-Bera
  - Shapiro-Wilk
  - Anderson-Darling
- Automatic plotting of trading volume timelines with event day highlighted

## Dependencies
Required packages:
```
pip install pandas matplotlib scipy tqdm wrds
```

## Usage
### 1. Setup
```
from trading_activity_analyzer import TradingActivityAnalyzer
import pandas as pd

sample_data = pd.DataFrame({
    'trans_date': pd.to_datetime(['2021-06-15', '2022-01-10', '2021-03-05']),
    'permno': [14593, 10107, 11869]
})

analyzer = TradingActivityAnalyzer(
    data=sample_data,
    period_start=-5,
    period_end=6,
    year_start=2020,
    year_end=2023,
    output_dir='./results/'
)

# Run full analysis
analyzer.check_trading_activity(test='Jarque-Bera', plot=True)
```
### 2. Custom Testing/Plotting
If you want to reuse fetched data and run different tests separately:
```
analyzer.test_activity_normality(test='Shapiro-Wilk')
analyzer.test_activity_normality(test='Anderson-Darling')
analyzer.plot_trading_activity()
```

## Notes
- Make sure your WRDS connection is active and has access to the `crsp.dsf` table.
- `period_start` and `period_end` are relative offsets from the event date (`trans_date`), and support both negative (before) and positive (after) days.
- Anderson-Darling test uses the 5% significance level critical value by default.

Author: Zhizhe Liu
Collaborator: Andrea Tillet
