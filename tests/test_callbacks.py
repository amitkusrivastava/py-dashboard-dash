import datetime as dt

import pandas as pd

from dashboard.callbacks import Filters, _filter_df


def make_df():
    data = [
        {"date": dt.date(2025, 1, 1), "product":"A","region":"EMEA","system":"Core","team":"Data","owner":"alice","status":"Green","revenue":100.0,"cost":60.0,"profit":40.0},
        {"date": dt.date(2025, 1, 2), "product":"B","region":"APAC","system":"Web","team":"Platform","owner":"bob","status":"Red","revenue":50.0,"cost":80.0,"profit":-30.0},
        {"date": dt.date(2025, 1, 3), "product":"A","region":"EMEA","system":"Core","team":"Data","owner":"carol","status":"Amber","revenue":70.0,"cost":20.0,"profit":50.0},
    ]
    return pd.DataFrame(data)


def test_filters_validation_lists_and_query():
    f = Filters(products="A", regions=["EMEA"], systems=None, teams="Data", owner_query="  Alice  ")
    assert f.products == ["A"]
    assert f.regions == ["EMEA"]
    assert f.teams == ["Data"]
    assert f.owner_query == "Alice"


def test_filter_df_all_parameters():
    df = make_df()
    out = _filter_df(
        df,
        start_date="2025-01-02",
        end_date="2025-01-03",
        products=["A","B"],
        regions=["APAC"],
        systems=["Web"],
        teams=None,
        min_profit=-100,
        owner_query="bo",
    )
    # Should match the second row only
    assert len(out) == 1
    assert out.iloc[0]["owner"] == "bob"


def test_filter_df_min_profit_and_owner_case_insensitive():
    df = make_df()
    out = _filter_df(
        df,
        start_date=None,
        end_date=None,
        products=["A"],
        regions=["EMEA"],
        systems=["Core"],
        teams=["Data"],
        min_profit=45,
        owner_query="CAR",
    )
    assert len(out) == 1
    assert out.iloc[0]["owner"] == "carol"
