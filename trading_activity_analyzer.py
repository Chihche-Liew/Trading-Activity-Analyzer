import os
import wrds
import pandas as pd
import matplotlib.pyplot as plt
from tqdm.notebook import tqdm
from scipy.stats import jarque_bera, shapiro, anderson
conn = wrds.Connection()


class TradingActivityAnalyzer:
    def __init__(self, data, period_start, period_end, year_start, year_end, output_dir='./results/'):
        self.data = data
        self.period_start = period_start
        self.period_end = period_end
        self.year_start = year_start
        self.year_end = year_end
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def _adjust_to_nearest_trading_day(date, trading_days):
        if date in trading_days:
            return date
        else:
            return min(trading_days, key=lambda x: abs((x - date).days))

    def _get_trading_range(self, trans_date, trading_days):
        trans_date = self._adjust_to_nearest_trading_day(trans_date, trading_days)
        trans_date_index = trading_days.index(trans_date)
        return trading_days[trans_date_index+self.period_start:trans_date_index+self.period_end]

    def fetch_trading_data(self):
        df = self.data.copy()
        trading_days = conn.raw_sql(
            f"""
            select distinct date from crsp.dsf
            where date between '{self.year_start}-01-01' and '{self.year_end}-12-31'
            """,
            date_cols=['date']
        )['date'].sort_values().tolist()
        df['period'] = df['trans_date'].apply(lambda x: self._get_trading_range(x, trading_days))
        df = df.explode('period')
        df['timeline'] = df.groupby(['trans_date', 'permno']).cumcount() + self.period_start
        dsf = conn.raw_sql(
            f"""
            select distinct permno, date, vol
            from crsp.dsf
            where date between '{self.year_start}-01-01' and '{self.year_end}-12-31'
            """,
            date_cols=['date']
        )
        df = df.merge(dsf, how='left', left_on=['permno', 'period'], right_on=['permno', 'date'])
        self.data = df

    def test_activity_normality(self, test='Jarque-Bera'):
        data = self.data.copy()
        results = []
        grouped_data = data.groupby(['trans_date', 'permno'])
        for (trans_date, permno), group in tqdm(grouped_data, desc="Testing normality"):
            vol = group['vol'].dropna()
            if len(vol) > 2:
                if test == 'Jarque-Bera':
                    stat, p_value = jarque_bera(vol)
                    reject = p_value < 0.05
                    results.append((trans_date, permno, 'Jarque-Bera', stat, p_value, reject))

                elif test == 'Shapiro-Wilk':
                    stat, p_value = shapiro(vol)
                    reject = p_value < 0.05
                    results.append((trans_date, permno, 'Shapiro-Wilk', stat, p_value, reject))

                elif test == 'Anderson-Darling':
                    result = anderson(vol)
                    stat = result.statistic
                    critical_values = result.critical_values[2]
                    significance_level = result.significance_level[2]
                    reject = stat > critical_values
                    results.append((trans_date, permno, 'Anderson-Darling', stat, critical_values, significance_level, reject))

        cols = ['trans_date', 'permno', 'test', 'statistic', 'p_value', 'reject']
        if test == 'Anderson-Darling':
            cols = ['trans_date', 'permno', 'test', 'statistic', 'critical_value', 'significance_level', 'reject']

        results = pd.DataFrame(results, columns=cols)
        results.to_csv(self.output_dir + 'trading_activity_' + test + '.csv', index=False)

    def plot_trading_activity(self):
        data = self.data.copy()
        output_dir = self.output_dir + 'images/'
        os.makedirs(output_dir, exist_ok=True)
        grouped_data = data.groupby(['trans_date', 'permno'])
        for (trans_date, permno), group in tqdm(grouped_data, desc="Plotting Vol"):
            plt.figure(figsize=(10, 6))
            plt.bar(group['timeline'], group['vol'], color='blue', alpha=0.6)
            plt.axvline(x=0, color='red', linestyle='--', linewidth=2)
            plt.xlabel('Timeline')
            plt.ylabel('Volume')
            plt.title(f'Volume over Time for {permno} on {trans_date.strftime('%Y-%m-%d')}')
            file_path = os.path.join(output_dir, f"{permno}_{trans_date.strftime('%Y-%m-%d')}.png")
            plt.savefig(file_path)
            plt.close()

    def check_trading_activity(self, test, plot=False):
        self.fetch_trading_data()
        # None, 'Jarque-Bera', 'Shapiro-Wilk', 'Anderson-Darling'
        if test:
            self.test_activity_normality(test)
        if plot:
            self.plot_trading_activity()


if __name__ == '__main__':
    if conn is None:
        print("Cannot run example: WRDS connection not established.")
    else:
        # sample input data
        sample_data = pd.DataFrame({
            'trans_date': pd.to_datetime(['2021-06-15', '2022-01-10', '2021-03-05']),
            'permno': [14593, 10107, 11869]
        })

        event_window_start_offset = -5
        event_window_end_offset = 6

        crsp_year_start = 2020
        crsp_year_end = 2023

        results_directory = './trading_activity_analysis_results/'

        analyzer = TradingActivityAnalyzer(
            data=sample_data,
            period_start=event_window_start_offset,
            period_end=event_window_end_offset,
            year_start=crsp_year_start,
            year_end=crsp_year_end,
            output_dir=results_directory
        )

        # Example 1: Fetch data, run Jarque-Bera test, and generate plots
        analyzer.check_trading_activity(test='Jarque-Bera', plot=True)

        # Note: Calling check_trading_activity again on the SAME analyzer instance
        # will call fetch_trading_data again, which re-assigns self.data.
        # If you want to test different things on the *same fetched data*, call test/plot methods directly:

        # analyzer.test_activity_normality(test='Shapiro-Wilk')
        # analyzer.test_activity_normality(test='Anderson-Darling')


        # Example 2: Fetch data and only generate plots (no normality test)
        # print("\n--- Running Analysis (Only Plots) ---")
        # Re-initialize for a clean run if you want to ensure fetch is called again on original sample_data
        # analyzer_for_plotting_only = TradingActivityAnalyzer(
        #     data=sample_data,
        #     period_start=event_window_start_offset,
        #     period_end=event_window_end_offset,
        #     year_start=crsp_year_start,
        #     year_end=crsp_year_end,
        #     output_dir=results_directory
        # )
        # analyzer_for_plotting_only.check_trading_activity(test=None, plot=True)