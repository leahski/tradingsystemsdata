"""
Calculate performance for various technical trading systems and display the
results in table and graph form.

"""

# Imports
import copy

from tradingsystemsdata.marketdata import NorgateFunctions
from tradingsystemsdata.positions import Positions
from tradingsystemsdata.pnl import Profit
from tradingsystemsdata.reports import PerfReport
from tradingsystemsdata.signals import Signals, CalculateSignalData
from tradingsystemsdata.systems_params import system_params_dict
from tradingsystemsdata.targets import TradeTargets
from tradingsystemsdata.trades import Trades
from tradingsystemsdata.utils import Setup, Labels, Reformat


class TestStrategy():
    """
    Run a backtest over the chosen strategy

    Parameters
    ----------

    api_key : Str
        AlphaVantage API key. If not provided will look for
        'ALPHAVANTAGE_API_KEY' in the environment variables.
    asset_type : Str
        The alphavantage asset class type. The default is 'fx'.
    bench_source : Str, optional
        The data source to use for the benchmark data, either 'norgate',
        'alpha' or 'yahoo'. The default is 'norgate'.
    bench_ticker : Str, optional
        Underlying to use as benchmark. The default '$SPX'.
    commission : Float, optional
        The amount of commission charge to apply to each trade. The
        default is $0.00.
    ccy_1 : Str, optional
        Primary currency of pair to return. The default 'GBP'.
    ccy_2 : Str, optional
        Secondary currency of pair to return. The default 'USD'.
    end_date : Str, optional
        Date to end backtest. Format is YYYY-MM-DD.
    entry_acceleration_factor : Float
        The acceleration factor used in the Parabolic SAR entry signal.
        The default is 0.02.
    entry_overbought : Int, optional
        The overbought level to use in the entry strategy.
    entry_oversold : Int, optional
        The oversold level to use in the entry strategy.
    entry_period : Int, optional
        The number of days to use in the entry strategy. The default is 14.
    entry_threshold : Float
        The entry threshold used for momentum / volatility strategies.
        The default is 0 for momentum and 1.5 for volatility.
    entry_type : Str, optional
        The entry strategy. The default is '2ma'.
    equity : Float
        The initial account equity level. The default is $100,000.00.
    exit_acceleration_factor : Float
        The acceleration factor used in the Parabolic SAR exit signal.
        The default is 0.02.
    exit_amount : Float
        The dollar exit amount. The default is $1000.00.
    exit_oversold : Int, optional
        The oversold level to use in the exit strategy.
    exit_overbought : Int, optional
        The overbought level to use in the exit strategy.
    exit_period : Int, optional
        The number of days to use in the exit strategy. The default is 5.
    exit_threshold : Float
        The exit threshold used for the volatility strategy.
        The default is 1.
    exit_type : Str, optional
        The exit strategy. The default is 'trailing_stop'.
    lookback : Int, optional
        Number of business days to use for the backtest. The default is 750
        business days (circa 3 years).
    ma1 : Int, optional
        The first moving average period.
    ma2 : Int, optional
        The second moving average period.
    ma3 : Int, optional
        The third moving average period.
    ma4 : Int, optional
        The fourth moving average period.
    position_size : Int, optional
        The number of units to trade. The default is based on equity.
    pos_size_fixed : Bool
        Whether to used a fixed position size for all trades. The default
        is True.
    riskfree : Float, optional
        The riskfree interest rate. The default is 25bps.
    simple_ma : Bool, optional
        Whether to calculate a simple or exponential moving average. The
        default is True.
    sip_price : Bool
        Whether to set the SIP of the Parabolic SAR exit to n-day
        high / low or to the high of the previous trade. The default is
        False.
    slippage : Float, optional
        The amount of slippage to apply to traded prices in basis points.
        The default is 5 bps per unit.
    start_date : Str, optional
        Date to begin backtest. Format is YYYY-MM-DD.
    stop_amount : Float
        The dollar stop amount. The default is $500.00.
    stop_period : Int, optional
        The number of days to use in the stop strategy. The default is 5.
    stop_type : Str, optional
        The stop strategy. The default is 'initial_dollar'.
    ticker : Str, optional
        Underlying to test. The default '$SPX'.
    ticker_source : Str, optional
        The data source to use for the ticker data, either 'norgate',
        'alpha' or 'yahoo'. The default is 'norgate'.

    Returns
    -------
    Results
        Prints out performance data for the strategy and plots performance
        graph.

    """

    def __init__(self, **kwargs):

        # Import dictionary of default parameters
        self.default_dict = copy.deepcopy(system_params_dict)

        # Generate backtest
        params, tables, labels, norgate_name_dict = self.run_backtest(**kwargs)

        # Generate signals when graph isn't drawn.    
        params = CalculateSignalData.generate_signals(
            default_dict=self.default_dict, 
            params=params, 
            tables=tables
            )
        
        self.params = params
        self.tables = tables
        self.labels = labels
        self.norgate_name_dict = norgate_name_dict
 

    @staticmethod
    def run_backtest(**kwargs):
        """
        Generate strategy backtest

        Parameters
        ----------
        params : Dict
            Dictionary of parameters.

        Returns
        -------
        params : Dict
            Dictionary of parameters.
        tables : Dict
            Dictionary of tables.

        """

        params = {}
        tables = {}
        labels = {}

        # Longnames for Norgate Tickers
        norgate_name_dict = {}

        # Store initial inputs
        inputs = {}
        for key, value in kwargs.items():
            inputs[key] = value

        # Initialise system parameters
        params = Setup.init_params(inputs)

        # Longnames for Norgate Tickers
        if params['ticker_source'] == 'norgate':
            norgate_name_dict = NorgateFunctions.get_norgate_name_dict()
            params['asset_type'] = 'commodity'

        # if params['ticker_source'] == 'yahoo':
        #     params['asset_type'] = 'equity'

        # Create DataFrame of OHLC prices from NorgateData or Yahoo Finance
        tables = kwargs.get('tables', {})

        params, tables = Setup.prepare_data(params, tables)

        # Set the strategy labels
        labels  = {}
        labels['entry_label'], labels['exit_label'], \
            labels['stop_label'] = Labels.strategy_labels(
                params=params, default_dict=system_params_dict)

        # Generate initial trade data
        tables, params, raw_trade_price_dict = Signals.raw_entry_signals(
            tables=tables, params=params)

        # Create exit and stop targets
        tables['prices'] = TradeTargets.exit_and_stop_targets(
            prices=tables['prices'], params=params,
            trade_price_dict=raw_trade_price_dict)

        # Create exit and stop signals
        tables['prices'] = Signals.exit_and_stop_signals(
            prices=tables['prices'], params=params)

        # Prepare final signals
        tables = Signals.final_signals(params, tables)

        # Create trade and position data
        pos_dict = Positions.calc_positions(
            prices=tables['prices'],
            signal=tables['prices']['combined_signal'],
            start=params['start'])

        # Scale the position info by the position size
        pos_dict = Reformat.position_scale(
            pos_dict=pos_dict, position_size=tables['prices']['position_size'])

        # Map the raw positions to the OHLC data
        tables['prices'] = Reformat.map_to_prices(
            prices=tables['prices'],
            input_dict=pos_dict,
            title_modifier='')

        tables['prices']['trade_number'] = Trades.trade_numbers(
            prices=tables['prices'],
            end_of_day_position=tables['prices']['end_of_day_position'],
            start=params['start'])

        # Calculate the trades and pnl for the strategy
        tables['prices'] = Profit.profit_data(
            prices=tables['prices'],
            params=params)

        # Create monthly summary data
        tables['monthly_data'] = Profit.create_monthly_data(
            prices=tables['prices'], equity=params['equity'])

        # Create dictionary of performance data
        tables['perf_dict'] = PerfReport.performance_data(
            tables=tables, params=params, labels=labels,
            norgate_name_dict=norgate_name_dict)

        return params, tables, labels, norgate_name_dict


    @staticmethod
    def performance_report(input_dict: dict):
        """
        Display the performance report

        Parameters
        ----------
        tables : Dict
            Dictionary containing performance dict.

        Returns
        -------
        Prints the performance report to the console.

        """
        # Print out results
        PerfReport.report_table(input_dict=input_dict)


class TestPortfolio():
    """
    Run backtests over a portfolio of tickers

    """
    def __init__(self, **kwargs):

        #self.system_dict = self.run_individual_tests(**kwargs)
        self.system_dict = self.run_individual_tests_with_data(**kwargs)


    @staticmethod
    def run_individual_tests(portfolio: dict, **kwargs) -> dict:
        """
        Run backtests for each of the provided tickers.

        Parameters
        ----------
        portfolio : Dict
            Dictionary of lists of underlying tickers.
            commodities : List, optional
                List of commodity tickers in portfolio.
            stocks : List, optional
                List of stock tickers in portfolio.
            fx : List, optional
                List of fx tickers in portfolio.
            crypto : List, optional
                List of crypto tickers in portfolio.

        **kwargs : Dict
            All other keyword parameter.

        Returns
        -------
        system_dict : Dict
            Dictionary containing returns data for each underlying.

        """
        system_dict = {}
        # benchmark_calc = False
        for market, underlying_list in portfolio.items():
            print(market)
            for underlying in underlying_list:
                print(underlying)

                if market == 'commodities':
                    strat = TestStrategy(ticker=underlying,
                                         ticker_source='norgate',
                                         **kwargs)
                elif (market == 'equities'
                      and kwargs.get('equity_source', 'yahoo') == 'yahoo'):
                    strat = TestStrategy(ticker=underlying,
                                         ticker_source='yahoo',
                                         **kwargs)
                else:
                    strat = TestStrategy(ticker=underlying,
                                         ticker_source='alpha',
                                         **kwargs)

                system_dict[underlying] = {'model':strat}
                system_dict[underlying].update(
                    {'prices':strat.tables['prices']})
                system_dict[underlying].update(
                    {'monthly_data':strat.tables['monthly_data']})

        return system_dict


    @staticmethod
    def run_individual_tests_with_data(portfolio: dict, **kwargs) -> dict:
        """
        Run backtests for each of the provided tickers.

        Parameters
        ----------
        portfolio : Dict
            Dictionary of lists of underlying tickers.
            commodities : List, optional
                List of commodity tickers in portfolio.
            stocks : List, optional
                List of stock tickers in portfolio.
            fx : List, optional
                List of fx tickers in portfolio.
            crypto : List, optional
                List of crypto tickers in portfolio.

        **kwargs : Dict
            All other keyword parameter.

        Returns
        -------
        system_dict : Dict
            Dictionary containing returns data for each underlying.

        """
        system_dict = {}
        start_date = kwargs.get('start_date', None)
        end_date = kwargs.get('end_date', None)
        #data = kwargs.get('data', None)
        for market, underlying_dict in portfolio.items():
            print(market)
            for ticker, market_data in underlying_dict.items():
                print(ticker)
                #if data is not None:
                #    start = str(data[0][1].index[0].date())
                #    end = str(data[0][1].index[-1].date())
                #else:
                #    start is None
                #    end is None

                if market == 'commodities':
                    strat = TestStrategy(ticker=ticker,
                                         ticker_source='norgate',
                                         market_data=market_data,
                                         #start_date = start,
                                         #end_date = end,
                                         **kwargs)
                elif (market == 'equities'
                      and kwargs.get('equity_source', 'yahoo') == 'yahoo'):
                    strat = TestStrategy(ticker=ticker,
                                         ticker_source='yahoo',
                                         market_data=market_data,
                                         **kwargs)
                else:
                    strat = TestStrategy(ticker=ticker,
                                         ticker_source='alpha',
                                         market_data=market_data,
                                         **kwargs)

                system_dict[ticker] = {'model':strat}
                system_dict[ticker].update(
                    {'prices':strat.tables['prices']})
                system_dict[ticker].update(
                    {'monthly_data':strat.tables['monthly_data']})

                if start_date is None:
                    start_date = strat.params['start_date']
                if end_date is None:
                    end_date = strat.params['end_date']

        params = {}
        params['start_date'] = start_date
        params['end_date'] = end_date
        system_dict['benchmark'] = NorgateFunctions.return_norgate_data(
            '$SPX', params)

        return system_dict


    @staticmethod
    def prep_portfolio_list(
        top_ticker_list: list,
        portfolio: dict,
        asset_class: str,
        num_tickers: int) -> dict:
        """
        Prepare portfolio of tickers from top trend data

        Parameters
        ----------
        top_ticker list : list
            List of top trending tickers obtained from TrendStrength
            object: top_trends['top_ticker_list']
        portfolio : Dict
            Dictionary to contain asset classes and ticker lists.
        asset_class : Str
            String describing the asset class.
        num_tickers : Int
            The number of tickers to choose

        Returns
        -------
        portfolio : Dict
            Dictionary to contain asset classes and ticker lists..

        """
        #input_list = data.top_trends['top_ticker_list'][:num_tickers]
        input_list = top_ticker_list[:num_tickers]
        portfolio.update({asset_class:list(zip(*input_list))[0]})

        return portfolio


    @staticmethod
    def prep_portfolio_dict(
        top_ticker_dict: dict,
        portfolio: dict,
        asset_class: str,
        num_tickers: int) -> dict:
        """
        Prepare portfolio of tickers from top trend data

        Parameters
        ----------
        top_ticker_dict : dict
            Dictionary of top trending tickers obtained from TrendStrength
            object: top_trends['top_ticker_dict']
        portfolio : Dict
            Dictionary to contain asset classes and ticker lists.
        asset_class : Str
            String describing the asset class.
        num_tickers : Int
            The number of tickers to choose

        Returns
        -------
        portfolio : Dict
            Dictionary to contain asset classes and ticker lists..

        """
        input_dict = {}
        #for rank, pair in data.top_trends['top_ticker_dict'].items():
        for rank, pair in top_ticker_dict.items():
            if rank < num_tickers:
                input_dict[pair[0]] = pair[1]
        portfolio.update({asset_class:input_dict})

        return portfolio
